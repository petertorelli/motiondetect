#!/usr/bin/env bash

filename=$1

if [ ! -f $filename ] ; then 
	echo "$0: -E- First argument must be a valid file"
	exit -1
fi

echo "$0: -I- Extracting JPEG"

jpg=${filename%.*}.jpg

ffmpeg -v quiet -i $filename -ss 00:00:1.000 -vframes 1 -vf scale=100:-1 $jpg

if [ "$?" != "0" ] ; then
	echo "$0: -E- Failed to extract JPEG"
	exit -1
fi

URL="https://www.repete.io"
TOKEN_ENDPOINT="${URL}/liddycam/_token"
POST_ENDPOINT="${URL}/liddycam/_post"
KEY=`head -1 ~/.website-key-upload`
token=`curl --silent $TOKEN_ENDPOINT`
vtoken=`echo -n ${KEY}${token} | sha256sum | cut -f1 -d' '`

echo "$0: -I- POSTing '$filename'"

curl --silent \
	--data-urlencode vtoken=$vtoken \
	--data-urlencode filename=$filename \
	--data-urlencode "filedata@${filename}" \
	$POST_ENDPOINT

echo "$0: -I- POSTing '$jpg'"

curl --silent \
	--data-urlencode vtoken=$vtoken \
	--data-urlencode filename=$jpg \
	--data-urlencode "filedata@${jpg}" \
	$POST_ENDPOINT

echo "$0: -I- Cleaning up"

rm $jpg
rm $filename

echo "$0: -I- Done"

