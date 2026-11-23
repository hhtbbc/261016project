"""Read-only V34 provenance, header, and frozen sample verification."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import struct
import subprocess
from time import monotonic, process_time
from xml.etree import ElementTree

from cdflib import CDF
from netCDF4 import Dataset


ROOT = Path(__file__).resolve().parents[1]
BASE = '4e1829b3bfaf99abc166db3a99893fc52be8f9f3'
V33 = Path('experiments/thermosphere_zg_vertical_sensitivity_v33')
OUT = Path('experiments/thermosphere_zg_external_datum_v34')
CHECKS = {}


def check(name, passed):
    if not passed:
        raise ValueError(name)
    CHECKS[name] = True


def load(path):
    return json.loads(path.read_text())


def sha(path):
    with safe(path).open('rb') as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest()


def safe(path):
    path = (ROOT / path).resolve(strict=True)
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError('Invalid source path')
    return path


def admit(*, datum, grid, frame, control, domain):
    return all((datum, grid, frame, control, domain))


def native_header(path):
    with Dataset(safe(path), 'r') as model:
        return {
            key: dict(dimensions=list(model[key].dimensions),
                      unit=getattr(model[key], 'units', None),
                      description=model[key].long_name)
            for key in ('Z', 'ZG', 'DEN', 'ilev', 'lev', 'lat', 'lon')
        }


def observation_header(path):
    # The CDF reader is used for attribute metadata only.
    cdf = CDF(safe(path))
    attrs = cdf.globalattsget()
    fields = {key: cdf.varattsget(key) for key in ('latitude', 'longitude', 'altitude')}
    hdr_path = Path(path).with_suffix('.HDR')
    hdr = ElementTree.parse(safe(hdr_path)).getroot()
    return dict(title=attrs['TITLE'][0], time=attrs['TIME SYSTEM'][0], fields=fields,
                version=hdr.findtext('Fixed_Header/File_Version'),
                protocol=hdr.findtext('.//Ref_Doc'),
                creation=hdr.findtext('.//Creation_Date'),
                inputs=[item.text for item in hdr.findall('.//List_of_Input_File_Names/File_Name')],
                HDR_SHA256=sha(hdr_path))


def verify_frozen():
    publication = load(V33 / 'publication_SHA256.json')
    approved_manifest = subprocess.check_output(
        ['git', 'show', f'{BASE}:{V33}/publication_SHA256.json'])
    check('publication_manifest_at_V33_commit', approved_manifest ==
          (V33 / 'publication_SHA256.json').read_bytes())
    frozen = load(V33 / 'sample_freeze.json')
    pinned = dict(publication)
    for path, value in frozen['source_SHA256'].items():
        check(f'no_conflicting_pin:{path}', path not in pinned or pinned[path] == value)
        pinned[path] = value
    for path, value in pinned.items():
        check(f'SHA256:{path}', sha(path) == value)

    expected = set()
    windows = frozen['windows']
    check('four_development_windows', {(w['year'], w['cutoff']) for w in windows}
          == {(2021, 6), (2021, 18), (2022, 6), (2022, 18)} and len(windows) == 4)
    for window in windows:
        tag = f"{window['year']}/{window['cutoff']}"
        indices = window['indices']
        utc = window['utc']
        check(f'60_original_indices:{tag}', indices == list(range(0, 360, 6))
              and len(utc) == len(indices))
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        check(f'integral_UTC_seconds:{tag}', all(t.endswith('.000000000Z') for t in utc))
        times = [datetime.fromisoformat(t[:19] + '+00:00') - epoch for t in utc]
        encoded = b''.join(struct.pack('<q', (t.days * 86400 + t.seconds) * 10**9
                                       + t.microseconds * 1000) for t in times)
        utc_digest = hashlib.sha256(encoded).hexdigest()
        check(f'UTC_identity:{tag}', utc_digest == window['selected_utc_SHA256'])
        expected.update(zip([window['year']]*60, [window['cutoff']]*60, indices, utc, strict=True))
    with (V33 / 'query_gradients.csv').open(newline='') as f:
        actual = [(int(row['year']), int(row['cutoff']), int(row['index']), row['UTC'])
                  for row in csv.DictReader(f)]
    check('240_V33_sample_keys', len(actual) == len(expected) == frozen['samples'] == 240
          and set(actual) == expected)
    return frozen, pinned


def audit():
    wall, cpu = monotonic(), process_time()
    frozen, pinned = verify_frozen()
    sources = Path('third_party/TIEGCM2.0/src')
    read = lambda name: safe(sources / name).read_text(errors='replace').lower()
    check('fortran_height_identity', all(key in read('addiag.F') for key in (
        'zg(lev0,i,j) = z(lev0,i,j)', 'effective earth radius', 'z_lbc', 'geometric height zg')))
    check('geographic_spacing_and_model_gravity', all(key in read('cons.F') for key in (
        'ylatg(j) = -0.5*(pi-dlatg)', 'grav = 870.', '136.291/sqrt(2.)')))
    den = read('diags.F').split("short_name = 'den'", 1)[1].split('short_name', 1)[0]
    check('DEN_registration', all(key in den for key in ('total density', 'g/cm3', 'ilev', 'dt.f')))
    provider = safe('src/atmosphere/tiegcm_density_provider.py').read_text()
    check('formal_interface_gate_in_source', bool(re.search(r'raise .*EXTERNAL_DATUM_UNVERIFIED', provider)))
    eligible = dict(datum=False, grid=False, frame=False, control=False, domain=False)
    check('missing_evidence_rejects', not admit(**eligible))
    check('complete_hypothetical_evidence_accepts', admit(**dict.fromkeys(eligible, True)))
    for key in eligible:
        check(f'missing_{key}_alone_rejects', not admit(**(dict.fromkeys(eligible, True) | {key: False})))

    v21_index = safe('experiments/thermosphere_autumn_data_acquisition_v21/raw_data_index.csv')
    with v21_index.open(newline='') as stream:
        v21 = {row['path']: row['SHA256'] for row in csv.DictReader(stream)}
    results = {}
    verified_assets = dict(pinned)
    for window in frozen['windows']:
        year = window['year']
        if year in results:
            continue
        cdf = window['trajectory_CDF']
        vol, = window['model_volumes']
        for source in (cdf, vol):
            verified_assets[source['path']] = source['SHA256']
            check(f'original_SHA256:{source["path"]}', sha(source['path']) == source['SHA256'])
        header = observation_header(cdf['path'])
        model = native_header(vol['path'])
        check(f'{year}_CDF_HDR_contract', header['version'] == '0301'
              and header['time'] == 'UTC' and header['title'] == Path(cdf['path']).stem
              and header['protocol'] == 'SW-DS-DTU-GS-0001'
              and all(header['fields'][k]['UNITS'] == unit
                      for k, unit in [('latitude', 'deg'), ('longitude', 'deg'), ('altitude', 'm')])
              and any('MODA_SC_1B' in p and '0504.sp3' in p for p in header['inputs'])
              and any('ACCAPOD_2_' in p and '0401.cdf' in p for p in header['inputs']))
        check(f'{year}_native_units_and_levels', all(
            model[k]['unit'] == unit and model[k]['dimensions'] == ['time', 'ilev', 'lat', 'lon']
            for k, unit in [('Z', 'cm'), ('ZG', 'cm'), ('DEN', 'g/cm3')]))
        check(f'{year}_geographic_header', model['lat']['unit'] == 'degrees_north'
              and model['lon']['unit'] == 'degrees_east')
        hdr_path = str(Path(cdf['path']).with_suffix('.HDR'))
        check(f'{year}_HDR_V21_SHA256', header['HDR_SHA256'] == v21[hdr_path])
        verified_assets[hdr_path] = header['HDR_SHA256']
        results[year] = dict(CDF_HDR=header, NetCDF=model)

    with (OUT / 'independent_verification.json').open('x') as f:
        json.dump(dict(check_count=len(CHECKS), checks=CHECKS, verified_asset_count=len(verified_assets),
                       source_SHA256=verified_assets, metadata=results, controls_eligible=0,
                       evidence_gate=eligible, CDF_observation_values_read=0, model_field_values_read=0,
                       wall_s=monotonic()-wall, cpu_s=process_time()-cpu,
                       peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    audit()
