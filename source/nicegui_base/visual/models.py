from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

class IconCategory(StrEnum):
    NAVIGATION='navigation'; ACTIONS='actions'; DATA_CONTROLS='data-controls'; STATUS='status'; DATA='data'; FILES='files'; SYSTEM='system'; IDENTITY_SECURITY='identity-security'; TIME='time'; LAYOUT='layout'; COMMUNICATION='communication'; WORKFLOW='workflow'; SEMICONDUCTOR='semiconductor'

class IconSize(StrEnum):
    XS='xs'; SM='sm'; MD='md'; LG='lg'; XL='xl'

ICON_SIZE_PX={IconSize.XS:14,IconSize.SM:16,IconSize.MD:20,IconSize.LG:24,IconSize.XL:32}

@dataclass(frozen=True)
class IconDefinition:
    key:str
    category:str
    domain:str
    path:str
    aliases:tuple[str,...]=()
    theme:str='currentColor'
    source:str='nicegui-base-project-authored'
    license:str='NiceGUI Base project-authored asset'

@dataclass(frozen=True)
class IllustrationDefinition:
    key:str
    path:str
    category:str='state'
    theme:str='currentColor'

@dataclass(frozen=True)
class AssetValidationIssue:
    asset:str
    code:str
    message:str
