#!/usr/bin/env bash

filename=$1

URL="https://www.repete.io"
TOKEN_ENDPOINT="${URL}/liddycam/_token"
POST_ENDPOINT="${URL}/liddycam/_post"
KEY=`head -1 ~/.website-key-upload`

token=`curl --silent $TOKEN_ENDPOINT`
vtoken=`echo -n ${KEY}${token} | sha256sum | cut -f1 -d' '`
echo $KEY
echo $token
echo $vtoken
echo $filename

curl \
	--data-urlencode vtoken=$vtoken \
	--data-urlencode filename=$filename \
	--data-urlencode "filedata@${filename}" \
	$POST_ENDPOINT


jpg=${filename%.*}.jpg
ffmpeg -i $filename -ss 00:00:1.000 -vframes 1 -vf scale=100:-1 $jpg

curl \
	--data-urlencode vtoken=$vtoken \
	--data-urlencode filename=$jpg \
	--data-urlencode "filedata@${jpg}" \
	$POST_ENDPOINT

rm $jpg
rm $filename
