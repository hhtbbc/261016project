"""Offline preregistration helpers: dates, driver completeness and cost, no density API."""
from datetime import date,timedelta,datetime,timezone
import math
CANDIDATES=((2021,'summer','2021-06-21'),(2022,'summer','2022-06-21'),(2021,'autumn','2021-09-23'),(2022,'autumn','2022-09-23'),(2021,'winter','2021-12-21'),(2022,'winter','2022-12-21'))
def days(start,stop):
 if start>stop:raise ValueError('Reversed dates')
 return [start+timedelta(days=j) for j in range((stop-start).days+1)]
def support(target):
 t=date.fromisoformat(target);start=t-timedelta(days=14);stop=t+timedelta(days=2);raw_start=start-timedelta(days=2);raw_stop=stop+timedelta(days=2);solar_start=raw_start-timedelta(days=40);solar_stop=raw_stop+timedelta(days=40)
 return dict(target_date=str(t),start=str(start),stop=str(stop),raw_start=str(raw_start),raw_stop=str(raw_stop),solar_start=str(solar_start),solar_stop=str(solar_stop),run_days=(stop-start).days,steps=(stop-start).days*1440,primary_records=(stop-start).days+1,secondary_records=(stop-start).days*24,GPI_days=len(days(raw_start,raw_stop)),Kp_buckets=len(days(raw_start,raw_stop))*8,Fobs_days=len(days(solar_start,solar_stop)))
def kp_class(values,statuses):
 if len(values)!=8 or len(statuses)!=8 or not all(s=='def' for s in statuses) or not all(v is not None and math.isfinite(v) and 0<=v<=9 for v in values):return 'UNKNOWN'
 peak=max(values)
 return 'QUIET' if peak<=2 else ('ENHANCED' if peak>=5 else 'INTERMEDIATE')
def valid_solar(v):return v is not None and math.isfinite(v) and v>0

def centered(solar,day):
 required=[day+timedelta(days=j) for j in range(-40,41)];bad=[d for d in required if not valid_solar(solar.get(d))]
 return (None,bad) if bad else (sum(solar[d] for d in required)/81,[])
def seed_status(actual_present,complete_primary,clock_ok,season_qualified):
 if not actual_present:return 'NOT_ACQUIRED'
 if not complete_primary or not clock_ok:return 'BLOCKED_IDENTITY_OR_CLOCK'
 return 'QUALIFIED_FOR_REVIEW' if season_qualified else 'LEGAL_STRUCTURE_SEASON_ADAPTATION_UNVERIFIED'
def estimate(evidence,days_per_run,count):
 steps=days_per_run*1440;wall=[x['wall_s']/x['steps']*steps for x in evidence];vol=[x['output_bytes']/x['days']*days_per_run for x in evidence];cpu=[x['CPU_s']/x['steps']*steps for x in evidence if x.get('CPU_s') is not None]
 return dict(runs=count,days_per_run=days_per_run,steps_per_run=steps,total_steps=steps*count,wall_s_per_run_min=min(wall),wall_s_per_run_max=max(wall),total_wall_s_min=min(wall)*count,total_wall_s_max=max(wall)*count,soft_planning_s_per_run=max(wall)*1.5,total_soft_planning_s=max(wall)*1.5*count,requested_hard_s_per_run=4800,requested_total_hard_model_s=4800*count,CPU_core_hours_total_min=min(cpu)*count/3600,CPU_core_hours_total_max=max(cpu)*count/3600,output_bytes_per_run_min=min(vol),output_bytes_per_run_max=max(vol),total_output_bytes_max=max(vol)*count,sequential_peak_RSS_budget_GiB=16,output_cap_GiB_per_run=5,disk_floor_GiB=20,disk_available_if_reserving_all_output_caps_GiB=20+5*count,requested_engineering_s_per_run=600,requested_scoring_s_per_run=600,requested_verification_s_per_run=600,MPI=4,OMP=1,GPU=0,estimate_is_not_guarantee=True)

def core_protocol(base):
 keys=['cutoffs','history_hours','half_open','future_hours','nonoverlap_blocks','methods06','methods18','estimator','latitude_definitions','min_history_and_future_region_N','no_fallback','Stale06','future_poison_factor','freeze_parameters_before_future_metrics','joint','NA_never_PASS','metric_source','latitude_source','Map_A_source','operator_source','hourly_reader_source','no_IID_significance']
 return {k:base[k] for k in keys}
