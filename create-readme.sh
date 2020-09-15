if [ ! -d  "$1" ] ; then
   mkdir "$1"
   echo "This directory is part of a DEV, TEST or STAGE environment.  The data was not copied from the PRODUCTION site" > "$1/README.txt"
fi
