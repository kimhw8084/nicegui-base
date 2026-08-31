"""Canonical platform-neutral live reference laboratory.

The implementation originated as ``mac_lab`` during v1.4. v1.6 keeps that module
as a compatibility layer while this module is the supported public entrypoint.
"""
from .mac_lab import LAB_NAVIGATION, LAB_PORT, LAB_TITLE, LAB_VERSION, LabRoute, ROUTES, register_mac_lab_pages, run_mac_lab

register_live_lab_pages=register_mac_lab_pages
run_live_lab=run_mac_lab

__all__=['LAB_TITLE','LAB_VERSION','LAB_PORT','LAB_NAVIGATION','LabRoute','ROUTES','register_live_lab_pages','run_live_lab']
