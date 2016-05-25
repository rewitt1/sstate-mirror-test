# sstate-mirror-test

This is a quick script you can use to determine if you're experiencing problems downloading files from an sstate mirror. It uses similar logic to the OpenEmbedded sstate code but is a much simpler script to examine.

To run:
```
python ./mirror-test.py sstate-list-build-452 ~/sstate-downloads
```

Let the script run for a while, say 10-30 minutes, and then interrupt it with Ctrl+C (otherwise it will run indefinitely). `mirror-test.log` will have been written out with the results. Note that you will need sufficient disk space available for the downloads - which can be deleted afterwards.
