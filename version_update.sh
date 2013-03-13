#! /bin/bash
#
# This script updates the version number in all necessary places
# throughout the project, and adds a new entry to debian/changelog.
#
DATE_STR=`date +"%a, %d %b %Y %H:%M:%S +0100"`
VERSION_FILES=('setup.py' 'source/RPIO/__init__.py' 'source/c_gpio/py_gpio.c' 'source/c_pwm/pwm_py.c' 'documentation/source/conf.py');
VERSION_LAST=`head -n1 debian/changelog | awk '{print $2}' | sed "s/[()]//g"`

if [ "$1" == "--show" ]; then
    echo $VERSION_LAST
    exit 0
fi

echo "The last version is $VERSION_LAST."
echo -n "New version number: "
read version

if [ -e $version ]; then
    exit 1
fi

echo -n "Are you sure you want to update the project to v$version? [y/n] "
read confirm

if [ -e $confirm ]; then
    exit 1
fi

echo "Updating project to v$version..."
for fn in ${VERSION_FILES[@]}; do 
    echo "- $fn";
    #echo $cmd
    sed -i '' "s/$VERSION_LAST/$version/g" $fn
done

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

# Now rebuild doc for latest version
echo "Run 'make doc' now, to build documentation with the new version number"