# Swarm0601受力输入技术问题（仅草稿，未发送）

收件团队及邮箱尚未核实，不编造邮箱，不自动发送。请求版本适用的文档/样例，不请求绕过权限。

**Subject: Swarm-A0601 attitude, cross-section and thruster semantics for2023-01-04**

Dear Swarm product support team,

We are validating physical inputs for reproducible orbit propagation, without fitting aerodynamic parameters to the validation orbit. We downloaded the official SC_ADYN and STRAATT0601 products for2023-01-04. Their processors are ACCELE/03.25 and ORBATT/03.25; the products were reprocessed in July2025.

Could you help confirm the version-applicable definitions below?

1. STRAATT q declares ITRF <- S/C. What are the stored component order, quaternion algebra and exact vector transformation equation? What is the applicable body-frame definition and ITRF realization?
2. SC_ADYN A_head/right/left/down are3-component orbit-frame cross-section vectors in m2. How is that orbit frame constructed? Are these complete area-normal surfaces, effective vectors or another representation? What geometry/visibility model is recommended for a projected drag area?
3. How are m_SC and its uncertainty/quality determined? Which0601 flags govern its use, and how should short-period record variations be interpreted?
4. In01:00–13:00UTC,82 records have positive dt_thr, while all nominal f_thr vectors are zero. Is f_thr a populated physical quantity for this baseline? What interval does dt_thr describe, and where are the channel direction, branch mapping and impulse calibration specified?
5. What are the exact0601 definitions of Flags_q, Flags_Platform, SyncStatus and Maneuver_Id, including code4? We do not infer these from another product or an old dictionary.
6. The STRAATT processing inputs list AUXAORBMAN_20140115T115151_20250701T202911_0355 and AUXAL1BPC_20230101T000000_20230701T000000_0109, with AUXAAOC_C_0006. Is there an authorized public route to the corresponding definitions/data, and a recommended Swarm geometry and gas-surface interaction model with a clearly defined reference area?

We have retained all raw quality codes, do not treat zero nominal thrust as proof of no thrust, and do not equate quaternion normalization with attitude validity. Any guidance on calibration limits and recommended validation examples would be appreciated.

Best regards,
[Name / affiliation]
