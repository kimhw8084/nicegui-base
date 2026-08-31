from __future__ import annotations
import argparse, hashlib, json, platform
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

RUNTIME_DEPENDENCIES = {'nicegui': NICEGUI_VERSION}
CERTIFICATION_DEPENDENCIES = {'playwright': '1.62.0', 'Pillow': '12.3.0'}
# Backward-compatible public alias; these remain optional certification-only dependencies.
LIVE_CERT_DEPENDENCIES = CERTIFICATION_DEPENDENCIES


def sha256_file(path:str|Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def build_spdx_sbom(*, name:str='nicegui-base', namespace:str|None=None)->dict[str,Any]:
    created=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    namespace=namespace or f'https://company.invalid/sbom/{name}/{FRAMEWORK_VERSION}'
    packages=[
        {
            'SPDXID':'SPDXRef-Package-nicegui-base','name':name,'versionInfo':FRAMEWORK_VERSION,
            'downloadLocation':'NOASSERTION','filesAnalyzed':False,'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION',
            'supplier':'Organization: Internal',
        },
    ]
    relationships=[]
    for dependency, version in RUNTIME_DEPENDENCIES.items():
        spdx_name=dependency.lower().replace('_','-'); spdx_id='SPDXRef-Package-'+spdx_name
        packages.append({
            'SPDXID':spdx_id,'name':dependency,'versionInfo':version,
            'downloadLocation':f'https://pypi.org/project/{dependency}/','filesAnalyzed':False,
            'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION',
            'externalRefs':[{'referenceCategory':'PACKAGE-MANAGER','referenceType':'purl','referenceLocator':f'pkg:pypi/{spdx_name}@{version}'}],
            'comment':'Production runtime dependency. The deployment requirements file is authoritative and resolves through the company-approved Python index.',
        })
        relationships.append({'spdxElementId':'SPDXRef-Package-nicegui-base','relationshipType':'DEPENDS_ON','relatedSpdxElement':spdx_id})
    for dependency, version in CERTIFICATION_DEPENDENCIES.items():
        spdx_name=dependency.lower().replace('_','-'); spdx_id='SPDXRef-Package-cert-'+spdx_name
        packages.append({
            'SPDXID':spdx_id,'name':dependency,'versionInfo':version,
            'downloadLocation':f'https://pypi.org/project/{dependency}/','filesAnalyzed':False,
            'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION',
            'externalRefs':[{'referenceCategory':'PACKAGE-MANAGER','referenceType':'purl','referenceLocator':f'pkg:pypi/{spdx_name}@{version}'}],
            'comment':'Optional browser/rendered-product certification dependency; not required for production runtime.',
        })
        relationships.append({'spdxElementId':spdx_id,'relationshipType':'OPTIONAL_DEPENDENCY_OF','relatedSpdxElement':'SPDXRef-Package-nicegui-base'})
    return {
        'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':f'{name}-{FRAMEWORK_VERSION}',
        'documentNamespace':namespace,
        'creationInfo':{'created':created,'creators':['Tool: nicegui-base-sbom','Organization: Internal']},
        'packages':packages,
        'relationships':relationships,
    }


def build_provenance(*, artifact:str|Path|None=None)->dict[str,Any]:
    result={
        'framework':'nicegui-base','framework_version':FRAMEWORK_VERSION,'nicegui_version':NICEGUI_VERSION,
        'python':platform.python_version(),'platform':platform.platform(),
        'generated_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
    }
    if artifact:
        p=Path(artifact); result['artifact']={'name':p.name,'sha256':sha256_file(p),'size_bytes':p.stat().st_size}
    return result


def write_json(data:dict[str,Any],path:str|Path)->Path:
    p=Path(path);p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8');return p


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description='Generate NiceGUI Base supply-chain metadata')
    parser.add_argument('--sbom',default='SBOM.spdx.json');parser.add_argument('--provenance',default='BUILD_PROVENANCE.json')
    parser.add_argument('--artifact')
    args=parser.parse_args(argv)
    write_json(build_spdx_sbom(),args.sbom);write_json(build_provenance(artifact=args.artifact),args.provenance)
    return 0

if __name__=='__main__':raise SystemExit(main())
