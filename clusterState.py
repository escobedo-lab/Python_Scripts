import os,itertools,sys,subprocess,shlex,re
import numpy as np
import matplotlib.pyplot as plt
#---------------------------------------------------------------------------------------#
# Run cmd on the command line as a subprocess
#---------------------------------------------------------------------------------------#
def shout(cmd):
	#print(cmd)
	p = subprocess.Popen( shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE )
	out, err = p.communicate()
	return out
#---------------------------------------------------------------------------------------#
# Generate dictionary of running jobs. Queries can be limited by user
#---------------------------------------------------------------------------------------#
def runList(keys, usr=None):
	kDict = { k:[] for k in keys }
	uStr = ""
	# All jobs
	if usr!=None:
		uStr = "-u %s" % usr
	out = shout('squeue %s' % uStr)
	jobList = np.array( [ x.split() for x in out.split('\n')[1:-1] ])
	jID = jobList[:,0].astype(np.int)
	WorkDir = []; JobName = [];
	for job in jID:
		out = shout('scontrol show job %d' % job)
		res2 = out
		res = dict(re.findall(r'(\w*)=([\w*{\.,\/\-}]+\w*)?-*', out))
		for key in keys:
			kDict[key].append( res[key] )
	return kDict
#---------------------------------------------------------------------------------------#
# Wrapper to check if job already submitted (e.g. using loop submissions)
#---------------------------------------------------------------------------------------#
def fexists(rDict, fname):
	# True If job is running currently
	runBool = False
	try:
		ind = rDict['JobName'].index(fname)
		if rDict['WorkDir'][ind] == os.getcwd():
			runBool = True
	except ValueError:
		pass
	return runBool
#---------------------------------------------------------------------------------------#
# Extract user specific entries for given keyword
#---------------------------------------------------------------------------------------#
def exUser(rDict, key, usr, partition=None):
	# User list from global dictionary
	USR = np.array( rDict['UserId'] )
	ind = (USR==usr)
	# Add filter by partition name
	if partition != None:
		PART = np.array( rDict['Partition'] )
		ind = (ind) & (PART==partition)
	return np.array( rDict[key] ) [ind]
#---------------------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------------------#
if __name__ == "__main__":
	partition = 'fe13'
	# Keywords in scontrol output
	queries = ['UserId', 'JobName', 'WorkDir', 'NumNodes', 'NumCPUs', 'Partition']
	rDict = runList(queries)#,  usr='as3833')
	USR, ucount = np.unique( np.array( rDict['UserId'] ) , return_counts=True)
#---------------------------------------------------------------------------------------#
	NumCPUs = []; NumNodes = [];
	# Loop over the unique set of users running jobs
	print('USER\t\tnJob\t\tnCPU\t\tnNode\n#%s#' % ('-'*50) )
	for ui, usr in enumerate(USR):
		# Corresponding index list
		# Extend based on keywords
		NumCPUs.append( exUser(rDict, 'NumCPUs', usr, partition=partition).astype(np.int).sum() )
		# Change to include hyphenations in the node lists
		_nn = sum([ int(x.split('-')[0]) for x in exUser(rDict, 'NumNodes', usr, partition=partition) ])
		NumNodes.append( _nn )
		outList = [ usr, ucount[ui], NumCPUs[-1], NumNodes[-1] ]
		print( '\t\t'.join(map(str,outList)) )
#---------------------------------------------------------------------------------------#
	# Plot
	fig, ax = plt.subplots()
	lcpu = ax.plot(range(len(USR)), NumCPUs, 'r-s', label='NumCPUs')
	axn = ax.twinx()
	lnode = axn.plot(range(len(USR)), NumNodes, 'g-o', label='NumNodes')
#---------------------------------------------------------------------------------------#
	ax.set_xlabel(r'Users')
	ax.set_ylabel(r'Resources')
	axn.set_ylabel(r'Nodes')
	ax.set_xlim([-0.5,len(USR)-0.5])
	ax.set_xticks(np.arange(len(USR)))
	ax.set_xticklabels(USR, rotation=45)
	lns = lcpu+lnode
	labs = [l.get_label() for l in lns]
	ax.legend(lns, labs, loc='best', frameon=False)
	plt.show()
