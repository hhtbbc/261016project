"""Inspect explicitly named handoffs and retain the scientific gates."""
import argparse
import hashlib
import json
import math
import os
import re
from urllib.parse import urlsplit

from admit_swarm_sp3_v55 import (
    STAGING, ACCEPTED, ROOT, safe_directory, bounded_json, targets, admit, validate,
)
from import_summer_handoff_v39 import open_bounded

DECLARATIONS={
    'GFZ_2021_evidence.json':('GFZ','dates','observation_definition'),
    'ESA_0301_delivery.json':('ESA','products','delivery_record'),
    'NCAR_ZG_evidence.json':('NCAR','ZG_zero_surface','vertical_direction','model_latitude','control_points'),
}
CONTROL_FIELDS=('id','UTC','longitude_deg','latitude_deg','external_XYZ_m','external_height_m',
    'ellipsoid','frame_realization','frame_epoch','reference_point','model_position','model_ZG_m',
    'allowed_transform','uncertainty_m','authority_source','independent_validation_source')
GATES=['OFFICIAL_PROVENANCE_UNVERIFIED','SP3_EXACT_PRODUCT_NOT_ACQUIRED',
       'EXTERNAL_DATUM_UNVERIFIED','GFZ_2021_GAP_UNRESOLVED','TARGET_DENSITY_SEALED',
       'FIXED_OFFSET_NOT_ADMITTED','V37_FORMAL_SCORING_NOT_AUTHORIZED']


def declaration(name,fields):
    path=STAGING/name
    if not os.path.lexists(path):
        return {'state':'NOT_ACQUIRED'}
    data=bounded_json(path)
    if not isinstance(data,dict) or data.get('issuer')!=fields[0]:
        raise ValueError('Unrecognized issuer declaration')
    if any(not data.get(k) for k in ('document_id','version_or_date','public_reference',*fields[1:])
           if k!='control_points'):
        raise ValueError('Missing required evidence metadata')
    if name.startswith('GFZ_'):
        dates=data['dates']
        if not isinstance(dates,list) or not set(dates)<={'2021-05-09','2021-06-16'}:
            raise ValueError('Unexpected GFZ evidence day')
    elif name.startswith('ESA_'):
        from admit_swarm_summer_v53 import PRODUCTS
        p=data['products']
        if not isinstance(p,list) or not set(p)<=set(PRODUCTS):
            raise ValueError('Unexpected 0301 product identity')
    else:
        points=data.get('control_points')
        if not isinstance(points,list) or len(points)>128:
            raise ValueError('Bounded control-point table required')
        for r in points:
            if not isinstance(r,dict) or set(CONTROL_FIELDS)-r.keys():
                raise ValueError('Incomplete control-point row')
            xyz=r['external_XYZ_m']
            if not isinstance(xyz,list) or len(xyz)!=3:
                raise ValueError('Expected terrestrial XYZ triplet')
            nums=xyz+[r[k] for k in ('longitude_deg','latitude_deg','external_height_m','model_ZG_m','uncertainty_m')]
            if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in nums):
                raise ValueError('Nonfinite control geometry or uncertainty')
            if abs(r['longitude_deg'])>180 or abs(r['latitude_deg'])>90 or r['uncertainty_m']<0:
                raise ValueError('Invalid control geometry or uncertainty')
        if len({r['id'] for r in points})!=len(points):
            raise ValueError('Repeated control identity')
    url=urlsplit(data['public_reference'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Use a public HTTPS reference with no private access parameters')
    attachments=data.get('attachments',[])
    if not isinstance(attachments,list) or len(attachments)>8:
        raise ValueError('Bounded attachment list required')
    receipts=[]
    for a in attachments:
        f=a['file']
        if not isinstance(f,str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.(pdf|txt|csv|json)',f) or f in DECLARATIONS:
            raise ValueError('Non-permitted attachment basename or type')
        path=STAGING/f
        stream,size=open_bounded(path,2*2**20)
        with stream:
            sha=hashlib.sha256(stream.read(2*2**20+1)).hexdigest()
        if sha!=a['sha256']:
            raise ValueError('Attachment hash mismatch')
        receipts.append({'file':f,'bytes':size,'SHA256':sha})
    return {'state':'RECEIVED_PENDING_AUTHORITY_REVIEW','document_id':data['document_id'],'attachments':receipts}


def check(accept_sp3=False):
    safe_directory(STAGING)
    safe_directory(ACCEPTED)
    check_rows={}
    for name,fields in DECLARATIONS.items():
        try:
            check_rows[name]=declaration(name,fields)
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            check_rows[name]={'state':'REJECTED','reason':str(exc)}
    for name in targets():
        source=STAGING/name
        destination=ACCEPTED/name
        try:
            if os.path.lexists(destination):
                safe_directory(destination)
                meta=bounded_json(destination/'source_claim.json')
                _,_,actual=validate(destination/name,meta)
                if bounded_json(destination/'receipt.json')!=actual:
                    raise ValueError('Accepted SP3 receipt mismatch')
                if os.path.lexists(source):
                    with open_bounded(source,20*2**20)[0] as stream:
                        if hashlib.sha256(stream.read(20*2**20+1)).hexdigest()!=actual['SHA256']:
                            raise ValueError('Same-name staging/accepted byte conflict')
                row={'state':'BYTE_AND_STRUCTURE_VERIFIED_PENDING_AUTHORITY_REVIEW','receipt':actual}
            elif os.path.lexists(source):
                meta=bounded_json(STAGING/(name+'.source.json'))
                if accept_sp3:
                    receipt=admit(name)
                    row={'state':'BYTE_AND_STRUCTURE_VERIFIED_PENDING_AUTHORITY_REVIEW','receipt':receipt}
                else:
                    _,_,receipt=validate(source,meta)
                    row={'state':'VALID_CANDIDATE_NOT_PUBLISHED','receipt':receipt}
            else:
                row={'state':'NOT_ACQUIRED'}
        except (ValueError,OSError,TypeError,KeyError,AttributeError,StopIteration) as exc:
            row={'state':'REJECTED_OR_INCOMPLETE','reason':str(exc)}
        check_rows[name]=row
    return dict(staging=str(STAGING.relative_to(ROOT)),candidates=check_rows,
        frozen_gates_unchanged=GATES,density_reads=0,new_model_runs=0,formal_scores=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--accept-sp3',action='store_true',help='Publish passing SP3 byte and structural receipts only')
    print(json.dumps(check(p.parse_args().accept_sp3),ensure_ascii=False,indent=2))
