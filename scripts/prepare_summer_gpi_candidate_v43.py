"""Write an isolated V43 candidate and independently verify all stored values."""
import json
import math
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from netCDF4 import Dataset

from audit_summer_assets_v38 import sealed_read
from preflight_summer_gfz_v42 import ROOT, frozen, sha
from prepare_tiegcm_training_drivers import GpiDriver, arrays, decode, write_gpi
from atmosphere.autumn_gpi_validation import DRIVER_ATOL, MEAN_ATOL, independent_at, schema

BASE = "13f2dc4ac4ff43903f6f35cf39e695f5b436e825"
V42 = "experiments/thermosphere_summer_download_preflight_v42"
V22 = "experiments/thermosphere_autumn_gpi_seed_policy_v22"
OUT = ROOT / "experiments/thermosphere_summer_gpi_candidate_v43"
FILE = OUT / "gpi_2022_summer_candidate_v43.nc"


def stamp(day):
    return datetime.fromisoformat(day).replace(tzinfo=timezone.utc)


RAW = stamp("2022-06-05")
SOLAR = stamp("2022-04-26")
START = stamp("2022-06-07")
STOP = stamp("2022-06-23")
DAYS = [RAW + timedelta(days=i) for i in range(21)]
YS = [int(t.strftime("%Y%j")) for t in DAYS]
SOLAR_GRID = {SOLAR + timedelta(days=i) for i in range(101)}
KP_GRID = {t + timedelta(hours=h) for t in DAYS for h in range(0, 24, 3)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path):
    data = (ROOT / path).read_bytes()
    require(data == subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT), path)
    return json.loads(data)


def checked(data, expected):
    require(sha(data) == expected, "Source SHA mismatch")
    return json.loads(data)


def dump(name, data):
    with (OUT / name).open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def protect():
    checks = frozen()
    for name in (f"{V42}/publication_SHA256.json", f"{V22}/sha256_manifest.json"):
        entries = pinned(name)
        if name.startswith(V22):
            for year in (2021, 2022):
                audit = pinned(f"{V22}/gpi_audit_{year}.json")
                path = f"{V22}/gpi_{year}_autumn.nc"
                entries[path] = audit["SHA256"]
        for path, expected in entries.items():
            require(sha((ROOT / path).read_bytes()) == expected, path)
        checks[name] = len(entries)
    return checks


def raw_records(payload, key):
    require(set(payload) & {"Fobs", "Fadj", "Kp"} == {key}, "Wrong index identity")
    meta = payload.get("meta", {})
    units = payload.get("units", meta.get("units"))
    if isinstance(units, dict):
        units = units.get(key)
    require(meta.get("source") == "GFZ Potsdam" and units in (None, {"Fobs": "sfu", "Kp": "1"}[key]),
            "Wrong GFZ provenance or units")
    ticks = [datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
             for t in payload["datetime"]]
    values = payload[key]
    require(len(ticks) == len(set(ticks)) == len(values), "Duplicate or missing stamps")
    if key == "Kp":
        require(payload.get("status") == ["def"] * len(ticks), "Nondefinitive Kp")
    require(all(type(v) in (int, float) and math.isfinite(v) and
                (v > 0 if key == "Fobs" else 0 <= v <= 9) for v in values), "Invalid driver")
    return dict(zip(ticks, values))


def coverage(solar, kp):
    require(set(solar) == SOLAR_GRID and set(kp) == KP_GRID, "Incorrect UTC coverage")


def inputs(sources, parser):
    solar, kp = {}, {}
    for path, expected in sources.items():
        key = "Kp" if Path(path).name.startswith("Kp_") else "Fobs"
        values = parser(checked((ROOT / path).read_bytes(), expected), key)
        destination, grid = (kp, KP_GRID) if key == "Kp" else (solar, SOLAR_GRID)
        if key == "Kp":
            require(set(values) == grid, "Invalid Kp grid")
        else:
            require(all(t.hour == t.minute == t.second == 0 for t in values), "Invalid Fobs UTC")
        for t, val in values.items():
            if t in grid:
                require(t not in destination, "Overlapping source UTC")
                destination[t] = val
    coverage(solar, kp)
    return solar, kp


def native(path, solar, kp):
    layout = schema(path)
    require(layout == schema(ROOT / V22 / "gpi_2022_autumn.nc"), "Wrong native schema")
    means = {t: math.fsum(solar[t + timedelta(days=i)] for i in range(-40, 41)) / 81 for t in DAYS}
    with Dataset(path) as n:
        require((int(n.yearday_beg), int(n.yearday_end)) == (YS[2], YS[-3])
                and n.time_standard == "UTC" and n.averaging_window_days == 81
                and n.averaging_kind == "centered", "Wrong valid interval or average metadata")
        values = {}
        for name, variable in n.variables.items():
            arr = variable[:]
            require(not np.ma.getmaskarray(arr).any() and np.isfinite(arr).all(), "Masked or nonfinite driver")
            values[name] = np.asarray(arr)
    for name, expected in (("year_day", YS), ("f107d", [solar[t] for t in DAYS]),
                           ("kp", [kp[t] for t in sorted(KP_GRID)])):
        require(np.array_equal(values[name].ravel(), expected), f"Wrong {name} nodes")
    delta = max(abs(values["f107a"] - [means[t] for t in DAYS]))
    require(delta < MEAN_ATOL, "Wrong centered 81-day means")
    return means, dict(schema=layout, dimensions={"ndays": 21, "nkp": 8}, year_day=YS,
                       valid_year_day=[YS[2], YS[-3]], mean_max_abs_sfu=float(delta),
                       ranges={k: [float(v.min()), float(v.max())] for k, v in values.items()},
                       centered_means_sfu=values["f107a"].tolist(), missing_or_nonfinite=0)


def check_reader(path, solar, means, kp):
    driver = GpiDriver(path)
    ticks = {START + timedelta(minutes=i) for i in range(23041)}
    for t in DAYS[2:-2]:
        for sec in (1, 5399, 5401, 10799, 10801, 43199, 43201, 86399):
            tick = t + timedelta(seconds=sec)
            if tick <= STOP:
                ticks.add(tick)
    max_error = dict.fromkeys(("f107d", "f107a", "Kp", "hpower", "ctpoten"), 0.)
    endpoints = {}
    for t in sorted(ticks):
        yd = int(t.strftime("%Y%j"))
        actual = driver.at(yd, t.hour * 3600 + t.minute * 60 + t.second)
        expected = independent_at(t, solar, means, kp)
        for key, value in actual.items():
            delta = abs(value - expected[key])
            require(delta < DRIVER_ATOL, f"Driver {key} mismatch at {t}")
            max_error[key] = max(max_error[key], delta)
        if t in (START, STOP):
            endpoints[t.isoformat()] = actual
    return {"nodes": len(ticks), "minute_nodes": 23041, "max_abs_by_field": max_error, "endpoints": endpoints}


def tests(sources, solar, kp):
    checks = []
    def fails(name, call):
        try:
            call()
        except ValueError:
            checks.append(name)
            return
        raise AssertionError(f"Unexpected acceptance: {name}")

    source = next(iter(sources))
    checked((ROOT / source).read_bytes(), sources[source])
    checks.append("frozen source SHA accepted")
    fails("modified SHA", lambda: checked(b"{}", sources[source]))
    fails("missing Fobs", lambda: coverage({t: v for t, v in solar.items() if t != SOLAR}, kp))
    fails("missing Kp", lambda: coverage(solar, {t: v for t, v in kp.items() if t != RAW}))
    payload = {"datetime": ["2022-06-05T00:00:00Z"], "meta": {"source": "GFZ Potsdam"}}
    fails("nondefinitive Kp", lambda: raw_records(payload | {"Kp": [1], "status": ["pre"]}, "Kp"))
    fails("Fadj substituted", lambda: raw_records(payload | {"Fadj": [99]}, "Fobs"))
    fails("UTC shifted", lambda: coverage(solar, {t + timedelta(seconds=1): v for t, v in kp.items()}))
    fails("2021 missing marker", lambda: raw_records(
        payload | {"datetime": ["2021-06-16T00:00:00Z"], "Fobs": [-1]}, "Fobs"))
    fails("nonfinite raw source", lambda: raw_records(payload | {"Fobs": [math.nan]}, "Fobs"))
    fails("unseen density access", lambda: sealed_read(object(), "density", []))
    driver = GpiDriver(FILE)
    fails("day beyond padding", lambda: driver.at(YS[-2], 0))
    fails("24:00 rejected", lambda: driver.at(YS[2], 86400))
    require(date(2020, 2, 29).strftime("%Y%j") == "2020060"
            and date(2020, 3, 1).strftime("%Y%j") == "2020061"
            and date(2022, 3, 1).strftime("%Y%j") == "2022060", "Leap day mapping")
    checks.append("leap and ordinary year index")
    with TemporaryDirectory(dir=OUT) as area:
        wrong = Path(area) / "wrong_schema.nc"
        with Dataset(wrong, "w", format="NETCDF3_CLASSIC") as n:
            n.createDimension("nkp", 7)
        fails("incorrect native dimensions", lambda: native(wrong, solar, kp))
        for name, field, value in (("altered mean", "f107a", 42), ("nonfinite NetCDF", "kp", math.nan)):
            fixture = Path(area) / (field + ".nc")
            fixture.write_bytes(FILE.read_bytes())
            with Dataset(fixture, "r+") as n:
                n[field][0] = value
            fails(name, lambda: native(fixture, solar, kp))
    return checks


def main():
    require(OUT.resolve() == OUT and OUT.is_dir() and not FILE.exists() and not FILE.is_symlink(),
            "Unsafe destination or candidate already exists")
    history = protect()
    preflight = pinned(f"{V42}/preflight.json")
    sources = preflight["sources_sha256"]
    require(len(sources) == 4, "Wrong V42 source count")
    code = pinned(f"{V22}/code_version_manifest.json")
    for path, expected in code.items():
        require(sha((ROOT / path).read_bytes()) == expected, path)
    release = pinned("experiments/thermosphere_autumn_mareqx_config_v23/execution_release.json")
    elf = "experiments/tiegcm2_apex2023_v1/tiegcm2.0"
    binary = (ROOT / elf).read_bytes()
    require(binary.startswith(b"\x7fELF") and sha(binary) == release["scientific_asset_SHA256"][elf], "ELF identity")
    solar, kp = inputs(sources, raw_records)
    build_solar, build_kp = inputs(sources, decode)
    result = arrays(build_solar, build_kp, RAW.date(), DAYS[-1].date())
    dump("input_freeze.json", {"status": "GPI_ENGINEERING_CANDIDATE", "base": BASE, "sources": sources,
         "algorithm_sha256": code, "generator_sha256": sha(Path(__file__).read_bytes()), "ELF_sha256": sha(binary),
         "source_Fobs_dates": ["2022-04-26", "2022-08-04"], "Fobs": 101, "Kp": 168,
         "utc_model_interval": [START.isoformat(), STOP.isoformat()], "step_seconds": 60, "steps": 23040,
         "candidate_only": True})
    write_gpi(FILE, *result, START.date(), STOP.date())
    with Dataset(FILE, "r+") as n:
        n.engineering_status = "GPI_ENGINEERING_CANDIDATE"
        n.authorized_for_model_run = "NO"
    FILE.chmod(0o444)
    means, details = native(FILE, solar, kp)
    reader = check_reader(FILE, solar, means, kp)
    checks = tests(sources, solar, kp)
    require(protect() == history, "Historical evidence changed")
    inputs(sources, raw_records)
    dump("verification.json", {"status": "GPI_ENGINEERING_CANDIDATE_VERIFIED", "numeric": "GPI_NUMERIC_VERIFIED",
        "fortran_static_contract": "MATCH", "model_runtime": "NOT_RUN", "RUN_READY": False,
        "path": str(FILE.relative_to(ROOT)), "sha256": sha(FILE.read_bytes()), "bytes": FILE.stat().st_size,
        "netcdf": details, "reader": reader, "tests": checks, "protected": history,
        "tolerances_strict": {"mean_sfu": MEAN_ATOL, "driver": DRIVER_ATOL},
        "new_model_runs": 0, "formal_input": 0, "GPU": 0, "unseen_target_density_reads": 0})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        dump("failure.json", {"error": repr(exc), "candidate_present": FILE.exists()})
        raise
