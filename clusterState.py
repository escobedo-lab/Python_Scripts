import os,subprocess,shlex,re
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
	for job in jID:
		out = shout('scontrol show job %d' % job)
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
def exUser(rDict, key, usr, partition=None, jstate=None):
	# User list from global dictionary
	USR = np.array( rDict['UserId'] )
	ind = (USR==usr)
	# Add filter by partition name
	if partition != None:
		PART = np.array( rDict['Partition'] )
		ind = (ind) & np.in1d(PART, partition)
	if jstate != None:
		JobState = np.array( rDict['JobState'] )
		ind = (ind) & (JobState==jstate)
	return np.array( rDict[key] ) [ind]
#---------------------------------------------------------------------------------------#
# Extract cluster limits
#---------------------------------------------------------------------------------------#
def limCluster(partition=None):
	keys = ['NodeName', 'CPUAlloc', 'CPUTot', 'Partitions']
	kDict = { k:[] for k in keys }
	out = shout('sinfo --Node --long')
	nID = np.array( [ x.split()[0] for x in out.split('\n')[2:-1] ])
	# Node ID
	for node in nID:
		out = shout('scontrol show node %s' % node)
		res = dict(re.findall(r'(\w*)=([\w*{\.,\/\-}]+\w*)?-*', out))
		for key in keys:
			kDict[key].append( res[key] )
	# Add filter by partition name
	if partition != None:
		PART = np.array( kDict['Partitions'] )
		ind = np.in1d(PART, partition)
	alloc = np.array( kDict['CPUAlloc'] ).astype(int) [ind]
	total = np.array( kDict['CPUTot'] ).astype(int) [ind]
	return np.array( kDict['NodeName'] ) [ind], alloc, total, total-alloc
#---------------------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------------------#
if __name__ == "__main__":
	sep = '#'+'-'*50+'#'
	# Set these parameters to None (not string) to include all possible data
	partition = ['fe13', 'plato', 'common']
#---------------------------------------------------------------------------------------#
# Cluster capacity
#---------------------------------------------------------------------------------------#
	nodeData = limCluster(partition=partition)
	nodeList, alloc, total, perc = nodeData 
	print('%s\nNode\t\tnAllocated\t\tnFree\t\t%%Free\n%s' % (sep, sep) )
	print("\n".join( [ "\t\t".join(map(str,y)) for y in np.array(nodeData).T ] ) )
	cperc = 100.0*sum(total-alloc)/sum(total)
	print("Total free %% = %f" % cperc )
#---------------------------------------------------------------------------------------#
	# Job state: None OR 'RUNNING' or 'PENDING'
	jstate = 'RUNNING'
	statep = 'PENDING'
	# Keywords in scontrol output
	queries = ['UserId', 'JobName', 'WorkDir', 'NumNodes', 'NumCPUs', 'Partition', 'JobState']
	rDict = runList(queries)
	USR, ucount = np.unique( np.array( rDict['UserId'] ) , return_counts=True)
#---------------------------------------------------------------------------------------#
	NumCPUs = []; NumNodes = []; NumCPUs2 = []; NumNodes2 = []
	# Loop over the unique set of users running jobs
	print('%s\nUSER\t\tnJob\t\tnCPU\t\tnNode\n%s' % (sep, sep) )
	for ui, usr in enumerate(USR):
		# Corresponding index list
		# Extend based on keywords
		NumCPUs.append( exUser(rDict, 'NumCPUs', usr, partition=partition, jstate=jstate).astype(np.int).sum() )
		# Change to include hyphenations in the node lists
		_nn = sum([ int(x.split('-')[0]) for x in exUser(rDict, 'NumNodes', usr, partition=partition, jstate=jstate) ])
		NumNodes.append( _nn )
		print( '%s\t\t%s\t\t%s (%0.3g%%)\t\t%s' % (usr, ucount[ui], NumCPUs[-1], 100.0*NumCPUs[-1]/sum(total), NumNodes[-1]) )
		NumCPUs2.append( exUser(rDict, 'NumCPUs', usr, partition=partition, jstate=statep).astype(np.int).sum() )
		# Change to include hyphenations in the node lists
		_nn = sum([ int(x.split('-')[0]) for x in exUser(rDict, 'NumNodes', usr, partition=partition, jstate=statep) ])
		NumNodes2.append( _nn )
#---------------------------------------------------------------------------------------#
	# Plot USER data
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

	#---------------------------------------------------------------------------------------#
	# Plot USER data PENDING
	fig2, ax2 = plt.subplots()
	lcpu2 = ax2.plot(range(len(USR)), NumCPUs2, 'r-s', label='NumCPUs')
#---------------------------------------------------------------------------------------#
	ax2.set_xlabel(r'Users')
	ax2.set_ylabel(r'Pending Resources')
	ax2.set_xlim([-0.5,len(USR)-0.5])
	ax2.set_xticks(np.arange(len(USR)))
	ax2.set_xticklabels(USR, rotation=45)
#---------------------------------------------------------------------------------------#
	# Plot cluster capacity
	figc, axc = plt.subplots()
	width = 0.75	
	lalloc = axc.bar(range(len(nodeList)), alloc, width, color='blue', label='Allocated')
	lfree = axc.bar(range(len(nodeList)), (total-alloc), width, color='orange', label='Free', bottom=alloc)
#---------------------------------------------------------------------------------------#
	axc.set_xlabel(r'Nodes')
	axc.set_ylabel(r'State')
	axc.set_xlim([-0.5,len(nodeList)+0.5])
	axc.set_xticks(np.arange(len(nodeList)))
	axc.set_xticklabels(nodeList, rotation=45)
	axc.legend(loc='best', frameon=False)
#---------------------------------------------------------------------------------------#
	plt.show()
