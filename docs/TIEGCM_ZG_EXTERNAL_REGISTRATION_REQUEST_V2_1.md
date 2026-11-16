# TIE-GCM ZG external registration — maintainer inquiry V2.1

Status: PREPARED / NOT SENT. V2 technical body is retained unchanged. No subscription, form or external contact has been performed.

## Contact and manual-sending preconditions

To: tgcmgroup@mailman.ucar.edu
From: [Name] <[Email]>
Affiliation: [Affiliation]

**Send only after the user has verified the current official route, successfully subscribed and received administrator approval.** The posting address and approval requirement are user-supplied for this revision. The specified Mailman page returned404 through two retrieval methods, so current policy, subscriber-only posting and closed-list status are not independently verified here. This is a conditional draft, not verified delivery readiness.

The official legacy contact page displays tgcmgroup@ucar.edu as a list contact/label; it is not silently used as the actual posting address. The official page also lists individual scientific contacts, but this package does not select or contact them.

Official sources: https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/contact.html and https://mailman.ucar.edu/mailman/listinfo/tgcmgroup . No current maintainer identity or successful delivery is implied.

## Formal English email

**Subject: TIE-GCM 2.0: geographic latitude, ZG zero surface, and registration to Swarm GRS80 geodetic heights**

Dear TIE-GCM maintainers,

We are preparing a reproducible comparison between TIE-GCM neutral mass density and Swarm-A POD-derived density. Before treating any satellite-to-model mapping as physically registered, we would appreciate clarification of the geographic-latitude and geometric-height conventions applicable to our version and configuration.

Our independent 2021/2022 runs use the pinned TIE-GCM 2.0 release (`da712811d925376ff8ef40ff64bda7cc070ca661`), with the official apex/IGRF update from NCAR commit `84185ee0b97307567c78e32ce85643b48a5cc1a9` and recorded GNU 12 build-compatibility overlays. The compiled height-chain routines `cons.F`, `lbc.F`, `addiag.F` and `getapex.F` are resolved from the unchanged 2.0 source tree. These independent runs are separate from the FourCastDEN authors' 2023 simulations; we do not claim identical configurations.

We use the 5° geographic grid, pressure-interface spacing 0.5, 60-second steps, 4 MPI ranks and OMP 1. Both runs have `ibgrddata=0` (no prescribed background lower-boundary data file), the default background `zbound=136.291/sqrt(2)*1.e5 cm`, and migrating diurnal/semidiurnal GSWM boundary forcing. Nonmigrating GSWM forcing is disabled. The two GSWM files are `gswm_diurn_5.0d_99km.nc` and `gswm_semi_5.0d_99km.nc`.

In our actual output, DEN and ZG both have dimensions `(time,ilev,lat,lon)` with 29 interfaces. DEN is in `g/cm3`, ZG in `cm`; we convert these to `kg/m3` and`m` using factors 1000 and 0.01. We do not substitute midpoint temperature/composition definitions for DEN's actual interface grid. The output version strings are `tiegcm_trunk` and`tiegcm2.0`; the pinned source/build provenance is supplied to disambiguate those strings.

Our source review finds that `addiag` initializes bottom Z from `z_lbc`; `calczg` sets bottom ZG equal to bottom Z, integrates upward using neutral temperature/composition and empirical latitude/height-dependent gravity, and constructs the top ZG interface by linear extrapolation. Its local effective gravity radius is not treated as an external reference-ellipsoid radius. Separately, the updated apex helper declares geodetic input coordinates and uses an equatorial radius 6378.160 km and inverse flattening 298.25; `getapex` passes model latitude values to that helper at a mapping altitude 130 km. We have not assumed that these magnetic-coordinate conventions define the thermodynamic ZG datum.

Could you please clarify the following four groups of questions for this 2.0 configuration?

**A. Model geographic latitude**

1. What is the intended definition of the native geographic grid latitude: geodetic latitude, geocentric latitude, or a spherical-model convention?
2. If geodetic, which reference ellipsoid and coordinate/frame convention apply? Does the apex helper's ellipsoid apply to the complete geographic model grid, or only to the magnetic-coordinate helper?
3. Is direct passage of model latitude to the geodetic apex interface an intended approximation, and are there version-specific qualifications?

**B. External zero surface of ZG and lower-boundary registration**

1. What external surface, if any, defines ZG=0: a specified ellipsoid, mean sea level/geoid, reference sphere, or an internal conventional altitude origin?
2. What is the reference surface and provenance of the default background `zbound`? Can its numerical value establish an external zero surface, or is an additional convention required?
3. Does setting bottom ZG equal to bottom geopotential Z involve an approximation relevant to external registration? How should GSWM-induced lower-boundary height perturbations and an alternative prescribed background be handled?
4. Are the apex ellipsoid and thermodynamic height reference explicitly linked anywhere, or should they be treated independently?

**C. Recommended registration for Swarm-A DNSAPOD_2**

We use instantaneous density from `SW_OPER_DNSAPOD_2_`, product version 0301, with the VirES official product contract describing GRS80 geodetic latitude/longitude and a height field in metres. The frozen HAPI description for `Height_GD` contains the apparent wording error “GRS80 latitude”; we retain that ambiguity rather than infer additional precision or frame information from it.

What version-appropriate procedure do you recommend for mapping these external GRS80 geodetic positions, or equivalent WGS84 positions, onto native model latitude and DEN/ZG columns? Please specify any needed reference-frame assumptions, horizontal transformation, vertical registration, and treatment of interface versus midpoint variables and top boundaries. Is there an official routine or worked along-track example we can verify independently?

Our present Map-A research hypothesis converts the original GRS80 geodetic location to nominal Earth-fixed Cartesian coordinates, expresses that same position as WGS84 geodetic coordinates, and explicitly approximates WGS84 latitude/ellipsoid height as model latitude/ZG. We then interpolate between two time frames and four horizontal columns, with log-density interpolation along each native ZG column; all eight columns must be valid and extrapolation is rejected. We have obtained 100% valid queries in selected windows, but **do not regard query coverage as evidence that this datum assumption is correct**. Our formal external density interface remains blocked.

**D. Accuracy and applicability if an exact mapping is unavailable**

If no strict external conversion exists, which approximation is recommended, and for what altitude, latitude and model configurations? What are the known error sources and any documented or validated error bounds? We would welcome references, test coordinates, uncertainty definitions, or example software. We do not wish to infer a height offset by minimizing observed density residuals, or to assign an unsupported accuracy bound to a convenient geometric approximation.

We have prepared a compact source/configuration manifest and can provide the specific line ranges and checksums listed below. We have not modified the height routines, fitted a height offset, or used apex constants as a ZG conversion. Clarification will guide a separate, independently tested registration review before any operational density adapter or physical orbit-validation claim.

Thank you for your guidance.

Best regards,
[Name]
[Affiliation]
[Email]

## Sanitized attachments only

Suggested: technical_summary_external.md, question_evidence_matrix_external.csv, configuration_summary_external.json. SENDING_GUIDE.md provides manual steps. Use only the V2.1 sanitized copies, not the original full manifest or original data. Sender placeholders must be filled by the user before sending.
