#! /bin/bash
#
# This script updates the version number in all necessary places throughout
# the project, and can add a new entry to debian/changelog.
#
# TODO: sed replaces all occurences (eg in RPIO/__init__.py). update to only update the right ones.
#
DATE_STR=`date +"%a, %d %b %Y %H:%M:%S +0100"`
VERSION_FILES=('setup.py' 'source/RPIO/__init__.py' 'source/c_gpio/py_gpio.c' 'source/c_pwm/pwm_py.c' 'documentation/source/conf.py');
VERSION_LAST=`cat VERSION`

if [ "$1" == "--show" ]; then
    echo $VERSION_LAST
    exit 0
fi

echo "Current Version: $VERSION_LAST"
echo -n "    New version: "
read version
if [ -e $version ]; then
    exit 1
fi

echo -n "Are you sure you want to update the project? [y/n] "
read confirm
if [ "$confirm" != "y" ]; then
    exit 1
fi

echo "Updating project to v$version..."
for fn in ${VERSION_FILES[@]}; do
    echo "- $fn";
    sed -i "s/$VERSION_LAST/$version/" $fn
done

echo $version > VERSION

echo -n "Do you want to update debian/changelog? [y/n] "
read confirm
if [ "$confirm" == "y" ]; then
    # Update Changelog
    echo "rpio ($version) unstable; urgency=low" > CHANGELOG.new
    echo "" >> CHANGELOG.new
    echo "  * " >> CHANGELOG.new
    echo "  * " >> CHANGELOG.new
    echo "  * " >> CHANGELOG.new
    echo "" >> CHANGELOG.new
    echo " -- Chris Hager <chris@linuxuser.at>  $DATE_STR" >> CHANGELOG.new
    echo "" >> CHANGELOG.new
    cat debian/changelog >> CHANGELOG.new
    mv CHANGELOG.new debian/changelog
    nano -w debian/changelog
fi

# Now rebuild doc for latest version
echo "Run 'make doc' now, to build documentation with the new version number"
