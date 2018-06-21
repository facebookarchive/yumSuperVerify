** THIS REPO HAS BEEN ARCHIVED AND IS NO LONGER BEING ACTIVELY MAINTAINED **

Check out [dcrpm](https://github.com/facebookincubator/dcrpm) instead.

# YumSuperVerify

YumSuperVerify is a utility to detect db corruption in Yum and RPM databases. Many tools exist to do this, but we've found that no utility so far that catches all kinds of corruption. This is our attempt at that.


## NOTES
For all the checks to work, you may need to run this as root depending on whether or not the current user has write access to .rpm.lock.

This binds rpm/yum which is only present in the system python
This means if you attempt to precompile this or run this with a runtime
besides the system runtime, it will probably fail.

This script will print a binary string which can be used if you're
curious on which portions of your databases are corrupted
There is also pretty output if run manually.

## Examples
```
18:03 $ sudo ./rpmdb_verify.py --fast  
[    INFO]      RPMDB    verify_transaction_set:         OK  
[    INFO]      RPMDB            verify_entries:         OK  
[    INFO]      RPMDB                 yum_check:         OK  
[    INFO]      YumDB         build_transaction:         OK  
0
```
## Requirements
Python2.7 interpreter  
rpm (binary must be in path)  
yum  

## Building
No building needed

## License
yumSuperVerify is BSD-licensed. We also provide an additional patent grant.
