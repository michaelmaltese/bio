#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import epb
import epb.controller
import time
import traceback

import cgi
import cgitb
cgitb.enable(format="text/plain")

def missing_param(param):
	print "Status: 400 Bad Request"
	print "Content-Type: text/plain"
	print
	print "Error: Missing parameter '%s'. Please try again, or contact the webmaster." % param
	print
	exit(0)

directory = "results"

form = cgi.FieldStorage()

sequence = form.getvalue("sequence", None)
if not sequence: missing_param('sequence')
method = form.getvalue("method", None)
if not method: missing_param('method')
categories = form.getlist("category")
if not categories: missing_param('category')

job_id = int(time.time())
# Shard the results into different folders, so we don't run into
# issues with directory size limits
job_shard = ("%06i" % (job_id % 999999))
job_shard = os.path.join(job_shard[:3], job_shard[3:])

output_directory = os.path.join(directory, job_shard, str(job_id))
os.makedirs(output_directory)

status = {"job": job_id, "steps": []}
status_file = os.path.join(output_directory, "status.html")
status_file_temp = status_file + "_temp"
with open(status_file, "w") as f:
	f.write(epb.controller.status(status))

print "Status: 302 Found"
print "Location: /%s" % status_file
print "Content-Type: text/plain"
print
#print status_file
print

sys.stdout.flush()

if os.fork(): exit(0)

sys.stdin.close()
sys.stdout.close()
sys.stderr.close()

os.close(0)
os.close(1)
os.close(2)

try:

	e = epb.EPB(os.path.dirname(epb.__file__))

	params = {
		"sequence": sequence,
		"method": method,
		"categories": categories
	}
	params.update(e.config)

	def callback(organism):
		global status
		status['steps'] = ["Blasting %s" % organism] + status['steps']
		with open(status_file_temp, "w") as f:
			f.write(epb.controller.status(status))
		os.rename(status_file_temp, status_file)

	results = epb.controller.results(params, callback)

	status['done'] = True
	with open(status_file_temp, "w") as f:
		f.write(epb.controller.status(status))
	os.rename(status_file_temp, status_file)

	results_file = os.path.join(output_directory, "results.html")
	with open(results_file, "w") as f:
		f.write(results)

except:
	status['done'] = True
	status['error'] = cgi.escape(traceback.format_exc())
	
	with open(status_file, "w") as f:
		f.write(epb.controller.status(status))
	os.rename(status_file_temp, status_file)