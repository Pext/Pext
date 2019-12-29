#!/bin/bash

min_percentage="$1"
weblate_json="$2"

printf '%s\n' "lupdate_only {" > pext/pext.pro
printf '%s\n' "SOURCES = qml/*" >> pext/pext.pro
printf '%s' "TRANSLATIONS = " >> pext/pext.pro

lang_percentages=$(curl --silent "$weblate_json" | jq -r '.[]  | "\(.code) \(.translated_percent)"')

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
oIFS=$IFS
IFS=$'\n'
for f in "$DIR"/pext/i18n/*.ts
do
  language_found=0
  lang_code=$(echo "$f" | sed 's/.*pext_\(.*\).ts/\1/')
  for lang_percentage in $lang_percentages
  do
    lang=$(echo "$lang_percentage" | awk -F' ' '{print $1}')
    # Weblate's API returns zh_Hant, but our filename is zh_TW
    # This ensures it does still match as it should
    if [ "$lang" == "zh_Hant" ]
    then
      lang="zh_TW"
    fi
    percentage=$(echo "$lang_percentage/1" | awk -F' ' '{print $2}' | bc)
    if [ "$lang" == "$lang_code" ]
    then
      language_found=1
      if [ "$percentage" -ge "$min_percentage" ]
      then
        printf '\\\n %s' "i18n/pext_$lang_code.ts " >> pext/pext.pro
        echo "$lang will be compiled"
      else
        echo "$lang will NOT be compiled"
      fi
      break
    fi
  done
  if [ "$language_found" -eq 0 ]
  then
    echo "COULD NOT DETERMINE STATUS OF $lang_code"
    exit 1
  fi
done
IFS=$oIFS

printf '\n}' >> pext/pext.pro
