# Technical summary for TIE-GCM maintainers

Purpose: clarify geographic latitude and external height registration before interpreting Swarm-A density comparisons physically. This is a source/configuration inquiry, not a request to validate density-error rankings.

Independent 2021/2022 B14 simulations use pinned TIE-GCM 2.0 commit `da712811d925376ff8ef40ff64bda7cc070ca661`, with official apex update `84185ee0b97307567c78e32ce85643b48a5cc1a9` and GNU 12 compatibility overlays. These independent runs are not claimed to match the FourCastDEN authors' 2023 configuration. Exact public source identifiers and necessary SHA256 values are in configuration_summary_external.json.

Both runs: 5° grid, 72x36 horizontal centres, 29 interfaces, pressure spacing 0.5, 60-second step, 4 MPI/OMP 1,default lower-boundary background (ibgrddata=0),migrating diurnal/semidiurnal GSWM enabled and nonmigrating GSWM disabled. 2021 runs March 9–26; 2022 March 9–25. Background zbound=136.291/sqrt(2)*1e5 cm, approximately 96.372290km; GSWM changes actual lower-boundary heights.

Height chain: bottom Z=z_lbc; bottom ZG=Z; calczg integrates temperature/composition with empirical latitude/height-dependent gravity and constructs the top ZG interface by extrapolation. The local effective gravity radius is not an external ellipsoid radius. The separate apex helper declares geodetic inputs and uses radius 6378.160km/inverse flattening 298.25; this alone does not establish the thermodynamic ZG datum.

Actual DEN/ZG dimensions are (time,ilev,lat,lon), 29 interfaces; units g/cm3 and cm, converted to kg/m3 and m by 1000 and 0.01. Equal-length lev and ilev arrays do not imply equal locations. Swarm-A instantaneous DNSAPOD 0301 density and GRS80 product coordinates are used, not orbit-mean density. The Height_GD contract wording ambiguity and unresolved terrestrial-frame realization remain explicit.

Map-A converts GRS80 geodetic positions via Earth-fixed Cartesian coordinates to WGS84 coordinates and explicitly assumes WGS84 latitude/ellipsoid height represent model latitude/ZG. All 8 time-space columns must be valid; no vertical extrapolation is allowed. 100% query coverage in selected windows does not demonstrate datum correctness.

We request clarification of: (A) full-model geographic latitude; (B) external ZG/zbound zero and boundary effects; (C) recommended Swarm GRS80/WGS84 registration; (D) validated approximation/error limits if an exact transform is unavailable. The seven-question CSV separates known implementation facts from unanswered external definitions.

No height offset has been fitted. No model height routines or operational density interface are changed. EXTERNAL_DATUM_UNVERIFIED remains in force. Any reply will undergo version applicability, independent mathematics and coordinate examples, error budget and common-domain review before a separate interface decision.
