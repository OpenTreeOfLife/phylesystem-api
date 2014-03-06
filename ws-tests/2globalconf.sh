#!/bin/sh
if test -f global.conf
then
    cp global.conf test.conf
else
    cp global.test.conf test.conf
fi