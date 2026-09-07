# Team acceptance — @D5_PACKAGE_ID@

Run these five checks from the extracted package directory and report `PASS`
or the exact blocker. No development-repository path is required.

- [ ] Install: `./install_d5.sh`
- [ ] Launch: `NGB_D5_PORT=8091 ./launch_d5.sh`
- [ ] Verify: `./verify_d5.sh`
- [ ] Create/export one app: complete the verifier’s Workbench path and confirm its evidence ZIP.
- [ ] Report `PASS` or classify the exact blocker as product defect, packaging defect, environment/company dependency, or user/setup error.
