"""Read-only summer GFZ audit. Any NetCDF written by this script is synthetic."""
import hashlib
import json
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from audit_summer_assets_v38 import sealed_read
from download_ncar_v40 import deliver_metadata, resume_headers, validate_reply
from observations.autumn_validation import check_product_stem
from prepare_tiegcm_training_drivers import GpiDriver, arrays, decode, write_gpi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/thermosphere_summer_download_preflight_v42"
BASE = "def64e24e26d56b2c027797eca9526b2bf78fbb2"
V38 = ROOT / "experiments/thermosphere_summer_data_acquisition_v38"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path):
    raw = (ROOT / path).read_bytes()
    anchor = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
    assert raw == anchor, path
    return raw


def frozen():
    results = {}
    for version in range(37, 42):
        path, = (ROOT / "experiments").glob(f"thermosphere_*_v{version}/publication_SHA256.json")
        raw = pinned(path.relative_to(ROOT))
        manifest = json.loads(raw)
        entries = manifest.get("published", manifest) | manifest.get("original_local_only", {})
        for name, expected in entries.items():
            assert sha((ROOT / name).read_bytes()) == expected, name
        results[f"V{version}"] = {"manifest_sha256": sha(raw), "entries": len(entries)}
    return results


def daily(year, month, day, count, hours):
    start = datetime(year, month, day, tzinfo=timezone.utc)
    return [start + timedelta(days=i, hours=h) for i in range(count) for h in hours]


def actual_drivers():
    march = json.loads(pinned("experiments/tiegcm_2022_mar25_preparation_v1/driver_source_audit.json"))
    autumn = json.loads(pinned("experiments/thermosphere_autumn_data_acquisition_v21/GFZ2022_raw_contract_audit.json"))
    summer = json.loads((V38 / "publication_SHA256.json").read_bytes())["original_local_only"]
    summer_solar, summer_kp = [next(p for p in summer if p.endswith(suffix)) for suffix in (
        "Fobs_2022-05-20_2022-07-28.json", "Kp_2022-06-05_2022-06-25.json")]
    expected_hashes = {
        march["sources"][0]["path"]: march["sources"][0]["SHA256"],
        summer_solar: summer[summer_solar],
        autumn["Fobs"]["source"]["path"]: autumn["Fobs"]["source"]["SHA256"],
        summer_kp: summer[summer_kp],
    }
    solar_times = daily(2022, 4, 26, 101, [0])
    kp_times = daily(2022, 6, 5, 21, range(0, 24, 3))
    source_counts = {}
    live = {"Fobs": {}, "Kp": {}}
    independent = {"Fobs": {}, "Kp": {}}
    for path, expected_hash in expected_hashes.items():
        data = (ROOT / path).read_bytes()
        assert sha(data) == expected_hash, path
        key, grid = ("Kp", kp_times) if path == summer_kp else ("Fobs", solar_times)
        primary = decode(json.loads(data), key)
        record = json.loads(data, parse_float=Decimal)
        utc = [datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
               for t in record["datetime"]]
        assert len(utc) == len(set(utc)) == len(record[key])
        if key == "Kp":
            assert utc == grid and record["status"] == ["def"] * len(grid)
        expected = set(grid)
        selected = {stamp: Decimal(value) for stamp, value in zip(utc, record[key], strict=True)
                    if stamp in expected}
        for stamp, value in selected.items():
            assert value.is_finite() and (0 <= value <= 9 if key == "Kp" else value > 0)
            assert stamp not in independent[key] or independent[key][stamp] == value
            independent[key][stamp] = value
        live[key].update({stamp: value for stamp, value in primary.items() if stamp in expected})
        source_counts[path] = len(selected)
    assert set(independent["Fobs"]) == set(solar_times)
    assert set(independent["Kp"]) == set(kp_times)
    days, flux, mean, kp = arrays(live["Fobs"], live["Kp"], date(2022, 6, 5), date(2022, 6, 25))
    centers = kp_times[::8]
    assert days == [stamp.date() for stamp in centers]
    expected_means = [float(sum(independent["Fobs"][stamp] for stamp in solar_times[i:i+81]) / 81)
                      for i in range(21)]
    np.testing.assert_array_equal(flux, [float(independent["Fobs"][t]) for t in centers])
    np.testing.assert_array_equal(kp.ravel(), [float(independent["Kp"][t]) for t in kp_times])
    np.testing.assert_allclose(mean, expected_means, rtol=1e-13, atol=0)
    np.testing.assert_array_equal(kp.shape, (21, 8))
    start, end = days[2], days[-3]
    assert (end - start).days * 1440 == 23040
    return {
        "status": "GFZ_PREFLIGHT_VERIFIED", "sources_sha256": expected_hashes,
        "source_counts": source_counts, "Fobs": len(solar_times), "definitive_Kp": len(kp_times),
        "centered_windows": len(mean), "independent_mean_max_abs_sfu": float(max(abs(mean - expected_means))),
        "target_Fobs_sfu": float(flux[16]), "target_centered_Fobs_sfu": float(mean[16]),
        "start_UTC": f"{start}T00:00:00Z", "stop_UTC": f"{end}T00:00:00Z",
        "year_day": [int(d.strftime("%Y%j")) for d in (start, end)], "minutes": 23040,
    }


def rejected(action):
    try:
        action()
    except (ValueError, RuntimeError):
        return
    raise AssertionError("Action accepted unexpectedly")


def fixtures():
    tests = []
    def check(name, action):
        action()
        tests.append(name)

    headers = {"Content-Type": "application/x-tar", "Content-Length": "2048",
               "ETag": '"fixture"', "Accept-Ranges": "bytes"}
    delivery = deliver_metadata("https://www.hao.ucar.edu/fixture", headers)
    check("HTML rejected", lambda: rejected(lambda: deliver_metadata(
        delivery["url"], headers | {"Content-Type": "text/html"})))
    check("same strong validator resume", lambda: np.testing.assert_equal(
        resume_headers(delivery, delivery.copy(), 512), {"Range": "bytes=512-", "If-Range": '"fixture"'}))
    check("changed validator rejected", lambda: rejected(lambda: resume_headers(
        delivery, delivery | {"etag": '"other"'}, 512)))
    check("weak validator rejected", lambda: rejected(lambda: resume_headers(
        delivery | {"etag": 'W/"fixture"'}, delivery | {"etag": 'W/"fixture"'}, 512)))
    reply = headers | {"Content-Range": "bytes 512-2047/2048", "Content-Length": "1536"}
    check("exact partial response", lambda: validate_reply(206, reply, delivery, 512))
    check("wrong partial length rejected", lambda: rejected(lambda: validate_reply(
        206, reply | {"Content-Length": "1535"}, delivery, 512)))
    check("full response during resume rejected", lambda: rejected(lambda: validate_reply(200, reply, delivery, 512)))
    stem = "SW_OPER_DNSAPOD_2__20220621T000000_20220621T235930_0301"
    check("registered ESA product accepted", lambda: np.testing.assert_equal(check_product_stem(stem, "2022-06-21"), stem))
    check("other ESA baseline rejected", lambda: rejected(lambda: check_product_stem(stem[:-4] + "0401", "2022-06-21")))
    check("unseen density rejected before read", lambda: rejected(lambda: sealed_read(object(), "density", [])))
    check("nondefinitive Kp rejected", lambda: rejected(lambda: decode(
        {"datetime": ["2022-06-05T00:00:00Z"], "Kp": [2], "status": ["pre"]}, "Kp")))
    with TemporaryDirectory(prefix="synthetic_", dir=OUT) as temp:
        days = [t.date() for t in daily(2000, 6, 5, 21, [0])]
        path = Path(temp) / "synthetic_fixture.nc"
        write_gpi(path, days, np.full(21, 123.0), np.full(21, 117.0),
                  np.broadcast_to(np.arange(8, dtype=float), (21, 8)), days[2], days[-3])
        driver = GpiDriver(path)
        check("synthetic start and stop padding", lambda: np.testing.assert_allclose(
            [driver.at(int(d.strftime("%Y%j")), 0)["f107d"] for d in (days[2], days[-3])], [123, 123]))
        check("synthetic Kp bucket center and midnight interpolation", lambda: np.testing.assert_allclose(
            [driver.at(2000159, s)["Kp"] for s in (5400, 16200, 0)], [0, 1, 3.5]))
        check("outside valid days rejected", lambda: rejected(lambda: driver.at(2000158, 0)))
        check("24:00 rejected", lambda: rejected(lambda: driver.at(2000159, 86400)))
    return tests


if __name__ == "__main__":
    before = frozen()
    code = {path: sha(pinned(path)) for path in (
        "scripts/prepare_tiegcm_training_drivers.py", "scripts/prepare_autumn_gpi_v22.py",
        "src/atmosphere/tiegcm_drivers.py",
    )}
    fortran = "third_party/TIEGCM2.0/src/gpi.F"
    code[fortran] = sha((ROOT / fortran).read_bytes())
    assert code[fortran] == json.loads(pinned("experiments/thermosphere_autumn_gpi_seed_policy_v22/code_version_manifest.json"))[fortran]
    result = actual_drivers()
    result["tests"] = fixtures()
    assert frozen() == before
    result.update(frozen=before, code_sha256=code, real_GPI_written=0, formal_input_written=0)
    print(json.dumps(result, indent=2))
