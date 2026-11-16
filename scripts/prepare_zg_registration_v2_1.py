"""Whitelist-only external share export. No network or messaging operations."""
from pathlib import Path
import json,csv,hashlib,time,resource,datetime
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_zg_external_registration_v2_1';OLD=R/'experiments/tiegcm_zg_external_registration_v2'
CONTACT='https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html';MAILMAN='https://mailman.ucar.edu/mailman/listinfo/tgcmgroup'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):
 p.resolve().relative_to(R)
 with p.open('x') as out:out.write(s)
def dump(p,x):put(p,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 t=time.perf_counter();cpu=time.process_time();E=F/'external_share';assert F.exists() and not list(E.iterdir()),'Existing export: refuse overwrite';protocol=json.loads((F/'protocol.json').read_text())
 for n,h in protocol['preserved_history_SHA256'].items():assert sha(R/n)==h,n
 m=json.loads((OLD/'model_configuration_manifest.json').read_text());fetch=json.loads((F/'mailman_fetch_local.json').read_text());assert fetch.get('error_type')=='HTTPError' and '404' in fetch['error']
 dump(F/'contact_route_evidence.json',dict(checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),official_pages=[dict(URL=CONTACT,retrieval='web read success',original_excerpts=['please subscribe to the moderated email list','may also contact the following HAO scientists'],displayed_list_name='tgcmgroup',displayed_address='tgcmgroup@ucar.edu',link_target='http://mailman.ucar.edu/mailman/listinfo/tgcmgroup',status='LEGACY_OFFICIAL_DOCUMENT_TEXT_VERIFIED',other_support='Legacy page lists individual HAO scientists for physics/chemistry/numerical/results questions; no individual addresses exported or contacted; current roles not established'),dict(URL=MAILMAN,retrieval='HTTP404 in web read and bounded HTTPS GET',original_excerpts=[],page_text_available=False,posting_address=None,subscription_required_to_post=None,administrator_approval_required=None,closed_list=None,status='CURRENT_MAILMAN_POLICY_NOT_VERIFIED')],user_supplied_claims=dict(posting_address='tgcmgroup@mailman.ucar.edu',subscription_requires_admin_approval=True,provenance='Explicit current task text; not independently verified page text',status='USER_SUPPLIED_PENDING_OFFICIAL_REVALIDATION'),prepared_sending_workflow=dict(To='tgcmgroup@mailman.ucar.edu',preconditions=['user verifies current official posting route','user successfully subscribes and receives administrator approval','user fills sender placeholders'],basis='User-requested conservative precondition, not a claim that currently retrieved policy proves subscriber-only posting'),not_equated_display_address_with_posting=True,delivery_test=False,current_maintainer_identity_verified=False,emails_sent=0,subscriptions=0,forms_submitted=0,only_two_allowed_page_URLs_accessed=True))
 base=m['base_release'];apex=m['apex_update'];config=dict(scope='Independent TIE-GCM runs; not the FourCastDEN authors original2023 configuration',official_source=dict(version=base['tag'],commit=base['commit'],URL='https://github.com/NCAR/tiegcm/tree/'+base['commit']),apex_update=dict(commit=apex['commit'],URL=apex['raw_url'],source_SHA256=apex['source_sha256'],patch_SHA256=apex['patch_sha256']),height_chain_source_SHA256={n:m['base_sources'][n]['SHA256'] for n in ['cons.F','lbc.F','addiag.F','getapex.F']},compiler_compatibility='Recorded GNU12 compatibility overlays; core height-chain routines unchanged',runs={},variables={},Swarm=dict(mission='Swarm',satellite='A',product_id='SW_OPER_DNSAPOD_2_',product_version='0301',density='instantaneous density, kg/m3',geodetic_contract='GRS80 geodetic latitude/longitude and height in metres; precise terrestrial frame realization not established',contract_wording_caveat='Height_GD prose contains the apparent latitude wording error; no additional datum accuracy inferred'),Map_A=dict(flow='GRS80 geodetic location -> nominal Earth-fixed Cartesian position -> WGS84 geodetic coordinates -> explicit assumption latitude=model latitude and ellipsoid height=native ZG',interpolation='two time frames x four horizontal columns, log-density interpolation along native ZG; all8columns valid; no extrapolation',status='PROVISIONAL; query coverage does not verify external height registration'),unresolved_gate='EXTERNAL_DATUM_UNVERIFIED')
 for y,c in m['B14_cases'].items():
  config['runs'][y]=dict(background='B14 official full smax initial state',start_UTC=c['actual_start'],stop_UTC=c['actual_stop'],source_record_day_hour_min=c['source_start'],horizontal_grid_degrees=5,latitude_centres=36,longitude_centres=72,pressure_interface_spacing=.5,**{k:c[k] for k in ['ibgrddata','STEP_s','MPI','OMP','zbound_formula','zbound_approx_km','GSWM_migrating_diurnal','GSWM_migrating_semidiurnal','GSWM_nonmigrating_diurnal','GSWM_nonmigrating_semidiurnal']},lower_boundary='default background zbound plus enabled GSWM height perturbations; external zero surface not established',engineering='PASS; does not imply full-state scientific quality or external datum validation')
  n=m['NetCDF_metadata'][y];config['variables'][y]={k:dict(dimensions=n['variables'][k]['dimensions'],units=n['variables'][k]['attributes']['units'],interface_count=29,SI_multiplier=1000 if k=='DEN' else .01) for k in ['DEN','ZG']}
 dump(E/'configuration_summary_external.json',config)
 GRID='https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html';APEX=apex['raw_url'];SRC='https://github.com/NCAR/tiegcm/tree/'+base['commit']+'/src';HAPI='https://vires.services/hapi/info?id=SW_OPER_DNSAPOD_2_'
 questions=[('Model geographic latitude','Regular geographic grid values are passed directly to apex_mall, which declares geodetic input.',SRC+'; '+APEX,'PARTIALLY_VERIFIED','Definition of the complete model geographic grid and applicable external ellipsoid/frame.'),('External zero of ZG','Bottom ZG equals bottom Z and z_lbc; geometric ZG is recommended for height comparison.',GRID+'; '+SRC,'UNVERIFIED','External reference surface: ellipsoid, geoid/sea level, sphere, or internal convention.'),('zbound reference surface','Default136.291/sqrt(2)*1e5 cm with background flag0; GSWM height perturbations are added.',SRC,'PARTIALLY_VERIFIED','External reference/provenance of the default boundary and any approximation from bottom ZG=Z.'),('apex ellipsoid versus thermodynamic heights','Updated apex uses radius6378.160km and inverse flattening298.25; the model passes mapping altitude130km.',APEX+'; '+SRC,'PARTIALLY_VERIFIED','Whether any explicit version-appropriate link exists between this helper ellipsoid and the thermodynamic ZG datum.'),('GRS80/WGS84 to model coordinates','Swarm product contract states GRS80 geodetic coordinates; Map-A is an explicit provisional hypothesis.',HAPI+'; '+GRID,'PARTIALLY_VERIFIED','Strict mapping to model latitude/ZG and applicable terrestrial frame assumptions.'),('Recommended along-track registration','ZG should be used for geometric registration; actual DEN/ZG in these outputs are both on ilev.',GRID+'; '+SRC,'PARTIALLY_VERIFIED','Official product-specific transformation/interpolation example and treatment of interface/top boundaries.'),('Accuracy and applicability','No applicable total external registration error bound has been established by this review.',GRID,'UNVERIFIED','Recommended approximation, validation examples, altitude/latitude limits and justified error bounds.')]
 with (E/'question_evidence_matrix_external.csv').open('x',newline='') as f:w=csv.writer(f,lineterminator='\n');w.writerow(['question','verified_facts','official_source_URLs','status','maintainer_confirmation_needed']);w.writerows(questions)
 summary='''# Technical summary for TIE-GCM maintainers

Purpose: clarify geographic latitude and external height registration before interpreting Swarm-A density comparisons physically. This is a source/configuration inquiry, not a request to validate density-error rankings.

Independent2021/2022 B14 simulations use pinned TIE-GCM2.0 commit`'''+base['commit']+'''`, with official apex update`'''+apex['commit']+'''` and GNU12 compatibility overlays. These independent runs are not claimed to match the FourCastDEN authors2023 configuration. Exact public source identifiers and necessary SHA256 values are in configuration_summary_external.json.

Both runs:5° grid,72x36 horizontal centres,29 interfaces,pressure spacing0.5,60-second step,4 MPI/OMP1,default lower-boundary background (ibgrddata0),migrating diurnal/semidiurnal GSWM enabled and nonmigrating GSWM disabled.2021 runs March9–26;2022 March9–25. Background zbound=136.291/sqrt(2)*1e5 cm, approximately96.372290km; GSWM changes actual lower-boundary heights.

Height chain: bottom Z=z_lbc; bottom ZG=Z; calczg integrates temperature/composition with empirical latitude/height-dependent gravity and constructs the top ZG interface by extrapolation. The local effective gravity radius is not an external ellipsoid radius. The separate apex helper declares geodetic inputs and uses radius6378.160km/inverse flattening298.25; this alone does not establish the thermodynamic ZG datum.

Actual DEN/ZG dimensions are(time,ilev,lat,lon),29 interfaces; units g/cm3 and cm, converted to kg/m3 and m by1000 and0.01. Equal-length lev and ilev arrays do not imply equal locations. Swarm-A instantaneous DNSAPOD0301 density and GRS80 product coordinates are used, not orbit-mean density. The Height_GD contract wording ambiguity and unresolved terrestrial-frame realization remain explicit.

Map-A converts GRS80 geodetic positions via Earth-fixed Cartesian coordinates to WGS84 coordinates and explicitly assumes WGS84 latitude/ellipsoid height represent model latitude/ZG. All8time-space columns must be valid; no vertical extrapolation is allowed.100% query coverage in selected windows does not demonstrate datum correctness.

We request clarification of: (A) full-model geographic latitude; (B) external ZG/zbound zero and boundary effects; (C) recommended Swarm GRS80/WGS84 registration; (D) validated approximation/error limits if an exact transform is unavailable. The seven-question CSV separates known implementation facts from unanswered external definitions.

No height offset has been fitted. No model height routines or operational density interface are changed. EXTERNAL_DATUM_UNVERIFIED remains in force. Any reply will undergo version applicability, independent mathematics and coordinate examples, error budget and common-domain review before a separate interface decision.
'''
 # Presentation-only spacing of the concise English summary.
 for a,b in [('Independent2021','Independent 2021'),('TIE-GCM2.0','TIE-GCM 2.0'),('commit`','commit `'),('update`','update `'),('GNU12','GNU 12'),('authors2023',"authors\' 2023"),('runs:5','runs: 5'),('grid,72','grid, 72'),('centres,29','centres, 29'),('interfaces,pressure','interfaces, pressure'),('spacing0.5,60','spacing 0.5, 60'),('step,4','step, 4'),('OMP1','OMP 1'),('ibgrddata0','ibgrddata=0'),('disabled.2021','disabled. 2021'),('March9','March 9'),(';2022','; 2022'),('approximately96','approximately 96'),('radius6378','radius 6378'),('flattening298','flattening 298'),('are(time','are (time'),('lon),29','lon), 29'),('by1000','by 1000'),('and0.01','and 0.01'),('DNSAPOD0301','DNSAPOD 0301'),('All8time','All 8 time'),('allowed.100%','allowed. 100%')]:summary=summary.replace(a,b)
 put(E/'technical_summary_external.md',summary)
 guide='''# Manual sending guide — not an automated action

## Route and evidence limitation

Prepared To: tgcmgroup@mailman.ucar.edu. This address and administrator-approval requirement were supplied in the task; the specified Mailman page currently returns HTTP404 in this review. They are not represented as independently verified current policy.

The legacy official contact page displays tgcmgroup@ucar.edu as the list label/address and directs readers to subscribe. Do not substitute that displayed address for the prepared posting address or assume the two aliases are equivalent.

Official subscription page: https://mailman.ucar.edu/mailman/listinfo/tgcmgroup
Official contact page: https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html

## Before the user sends anything

1. Manually recheck the specified official subscription page when available; confirm the posting address and current policy. If it remains unavailable, pause; this package does not establish delivery or current ownership.
2. Under the requested conservative workflow, personally subscribe using the page instructions, complete any confirmation step shown there and obtain administrator approval. No subscription or form is submitted by this package. Subscriber-only posting and closed-list status are currently unverified, rather than inferred from moderation alone.
3. Only after successful subscription/approval and route confirmation, fill [Name], [Affiliation] and [Email] in the V2.1 email. Use the subscribed sender address. Do not treat a prepared draft as already sent.
4. Review the technical wording and attach only the following three sanitized technical files. This guide can also be shared if useful.

## Suggested attachments

- technical_summary_external.md
- question_evidence_matrix_external.csv
- configuration_summary_external.json

Do not attach the original full configuration manifest, original model or observation data, complete execution records or query caches. This small export retains public source URLs, commits and necessary SHA256 identifiers without internal deployment details.

No specific person is designated by this package. The legacy contact page lists other scientific contacts, but no personal address is copied into these attachments or selected for communication.

EXTERNAL_DATUM_UNVERIFIED remains unchanged. Await an actual reply; do not implement a mapping merely because the question was sent.
'''
 put(E/'SENDING_GUIDE.md',guide)
 old=(R/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2.md').read_text();body=old.split('## Formal English email\n\n',1)[1].split('## Suggested lightweight attachments',1)[0]
 head='''# TIE-GCM ZG external registration — maintainer inquiry V2.1

Status: PREPARED / NOT SENT. V2 technical body is retained unchanged. No subscription, form or external contact has been performed.

## Contact and manual-sending preconditions

To: tgcmgroup@mailman.ucar.edu
From: [Name] <[Email]>
Affiliation: [Affiliation]

**Send only after the user has verified the current official route, successfully subscribed and received administrator approval.** The posting address and approval requirement are user-supplied for this revision. The specified Mailman page returned404 through two retrieval methods, so current policy, subscriber-only posting and closed-list status are not independently verified here. This is a conditional draft, not verified delivery readiness.

The official legacy contact page displays tgcmgroup@ucar.edu as a list contact/label; it is not silently used as the actual posting address. The official page also lists individual scientific contacts, but this package does not select or contact them.

Official sources: https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html and https://mailman.ucar.edu/mailman/listinfo/tgcmgroup . No current maintainer identity or successful delivery is implied.

## Formal English email

'''
 tail='''## Sanitized attachments only

Suggested: technical_summary_external.md, question_evidence_matrix_external.csv, configuration_summary_external.json. SENDING_GUIDE.md provides manual steps. Use only the V2.1 sanitized copies, not the original full manifest or original data. Sender placeholders must be filled by the user before sending.
'''
 put(R/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2_1.md',head+body+tail)
 dump(F/'external_share_manifest.json',dict(files={p.name:dict(SHA256=sha(p),bytes=p.stat().st_size) for p in E.iterdir()},generation='Explicit whitelist of scalar technical facts; original manifest not copied',technical_email_body_SHA256=hashlib.sha256(body.encode()).hexdigest(),technical_email_body_unchanged=True,attachments_ready_status='PENDING_INDEPENDENT_REDACTION_VALIDATION',contact_route_status='UNVERIFIED_HTTP404',manual_sending_ready=False))
 dump(F/'resource_audit.json',dict(preparation_wall_s=time.perf_counter()-t,preparation_CPU_s=time.process_time()-cpu,peak_process_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,metadata_fetch_wall_s=fetch['wall_s'],new_observation_download_bytes=0,model_integrations=0,GPU=0,DART=0,orbit=0,training=0,messages_sent=0,subscriptions=0,forms_submitted=0,scope='measured preparation process and bounded official-page GET; no continuous global sampling claimed'))
 dump(F/'commands.json',dict(environment='source scripts/activate_orbit.sh',preparation='python scripts/prepare_zg_registration_v2_1.py',validation='python scripts/verify_zg_registration_v2_1.py',web_read_URLs=[CONTACT,MAILMAN],bounded_GET='same exact Mailman URL,25s timeout,128KiB response bound,approved same-URL redirect only; HTTP404',no_send_command=True))
 print('Four whitelist exports and unchanged technical email generated; official route remains UNVERIFIED_HTTP404.')
if __name__=='__main__':main()
