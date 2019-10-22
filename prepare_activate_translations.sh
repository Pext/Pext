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
  lang_code=$(echo "$f" | sed 's/.*pext_\(.*\).ts/\1/')
  for lang_percentage in $lang_percentages
  do
    lang=$(echo "$lang_percentage" | awk -F' ' '{print $1}')
    percentage=$(echo "$lang_percentage/1" | awk -F' ' '{print $2}' | bc)
    if [ "$lang" == "$lang_code" ]
    then
      if [ "$percentage" -ge "$min_percentage" ]
      then
        printf '\\\n %s' "i18n/pext_$lang_code.ts " >> pext/pext.pro
      else
        echo "$lang will NOT be compiled"
      fi
    fi
  done
done
IFS=$oIFS

printf '\n}' >> pext/pext.pro
