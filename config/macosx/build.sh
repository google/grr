#!/bin/bash
#
# Script to build a MacOS-X package using PackageMaker
#

EXIT_SUCCESS=0;
EXIT_FAILURE=1;

HDIUTIL="/usr/bin/hdiutil";
PACKAGEMAKER="/Developer/Applications/Utilities/PackageMaker.app/Contents/MacOS/PackageMaker";

GRRBUILDPATH=$PWD;

FILES="config/macosx/grr-client.pmdoc/index.xml
       config/macosx/grr-client.pmdoc/01grrd-contents.xml
       config/macosx/grr-client.pmdoc/01grrd.xml
       config/macosx/grr-client.pmdoc/02com-contents.xml
       config/macosx/grr-client.pmdoc/02com.xml";

if [ ! -x "${PACKAGEMAKER}" ];
then
  echo "No such file: ${PACKAGEMAKER}";

  exit ${EXIT_FAILURE};
fi

if [ ! -x "${HDIUTIL}" ];
then
  echo "No such file: ${HDIUTIL}";

  exit ${EXIT_FAILURE};
fi

for CONFIGFILE in ${FILES};
do
  if [ ! -f ${CONFIGFILE}.in ];
  then
    echo "No such file: ${CONFIGFILE}.in";

    exit ${EXIT_FAILURE};
  fi
done

for CONFIGFILE in ${FILES};
do
  echo "Updating: ${CONFIGFILE}.in";

  sed "s?@GRRBUILDPATH@?${GRRBUILDPATH}?" "${CONFIGFILE}.in" > "${CONFIGFILE}";
done

${PACKAGEMAKER} --doc config/macosx/grr-client.pmdoc --out ../GRR.pkg

if [ $? -ne ${EXIT_SUCCESS} ];
then
  echo "Unable to create package: GRR.pkg.";

  exit ${EXIT_FAILURE};
fi

hdiutil create ../GRR.dmg -srcfolder ../GRR.pkg/ -fs HFS+

if [ $? -ne ${EXIT_SUCCESS} ];
then
  echo "Unable to create disk image: GRR.dmg.";

  exit ${EXIT_FAILURE};
fi

