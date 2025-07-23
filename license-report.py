#!/usr/bin/env python3
#
# Generates a CSV report on installed packages and their licenses.
# This script is meant to be run inside a running VyOS system.
#
# It's not perfect because not all Debian packages have license tags,
# some include the beginning of the license under the `License: ` tag,
# so such packages need to be inspected manually.
# Still gives some insights into the licenses we have in the image, though.
#
# License: MIT
#
# Permission is hereby granted, free of charge,
# to any person obtaining a copy of this software
# and associated documentation files (the "Software"),
# to deal in the Software without restriction,
# including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject
# to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import re
import sys

from vyos.utils.process import rc_cmd


if __name__ == '__main__':
    # Get a list of all package names
    # so that we can read their copyright files in /usr/share/doc/
    res, pkgs = rc_cmd(''' dpkg-query --show --showformat '${binary:Package}\n' ''')
    if res == 0:
        # Split the output into individual packages
        pkgs = pkgs.split('\n')

        # Remove architecture tags like ':amd64',
        # since they are not in /usr/share/doc/
        pkgs = list(map(lambda s: re.sub(r':(.*)$', r'', s), pkgs))
    else:
        print("Could not execute dpkg-query")
        sys.exit(1)

    # Gather license information from /usr/share/doc/
    report = []

    for p in pkgs:
        copyright = ""
        try:
            with open(f'/usr/share/doc/{p}/copyright', 'r') as f:
                copyright = f.read()
        except FileNotFoundError:
            print(f'Package {p} does not include a copyright file ', file=sys.stderr)
        except:
            print(f'Could not read the copyright file for package {p}', file=sys.stderr)

        # Extract license information
        # There may be multiple 'License:' lines in the file
        # if different files or parts of the package
        # are under different licenses.
        licenses = re.findall(r'License:\s+(.*)', copyright)

        # Deduplicate the list.
        # It's common to have multiple instances of the same license,
        # especially if files in a package are under the same license
        # but of a different origin.
        licenses = list(set(licenses))

        report.append((p, licenses))

    for (p, ls) in report:
        print(f'"{p}","{", ".join(ls)}"')
