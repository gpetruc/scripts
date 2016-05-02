#!/usr/bin/env python
# ---- by Alessandra Fanfani ----
# il trucco e' http://cmsweb.cern.ch/phedex/datasvc/xml/prod/lfn2pfn?node=T2_IT_Legnaro&lfn=/store/...&protocol=srmv2
import urllib
from xml.dom.minidom import parse
from urlparse import urlparse 

class PhEDExDatasvcInfo:
    def __init__( self , cfg_params ):
 
        ## PhEDEx Data Service URL
        url="https://cmsweb.cern.ch/phedex/datasvc/xml/prod"
        self.datasvc_url = cfg_params.get("USER.datasvc_url",url)

        self.protocol = 'srmv2'
        self.srm_version = 'srmv2'
        self.node = cfg_params.get('USER.storage_element',None)        
        self.user_lfn = cfg_params.get('USER.lfn','/store/user')
       
        return

    
    def lfn2pfn(self):
        """
        PhEDEx Data Service lfn2pfn call
 
        input:   LFN,node name,protocol
        returns: DOM object with the content of the PhEDEx Data Service call
        """  
        params = {'node' : self.node , 'lfn': self.lfn , 'protocol': self.protocol}
        params = urllib.urlencode(params)
        datasvc_lfn2pfn="%s/lfn2pfn"%self.datasvc_url
        urlresults = urllib.urlopen(datasvc_lfn2pfn, params)
        try:
            urlresults = parse(urlresults)
        except:
            urlresults = None

        return urlresults
 
    def parse_error(self,urlresults):
        """
        look for errors in the DOM object returned by PhEDEx Data Service call
        """
        errormsg = None 
        errors=urlresults.getElementsByTagName('error')
        for error in errors:
            errormsg=error.childNodes[0].data
            if len(error.childNodes)>1:
               errormsg+=error.childNodes[1].data
        return errormsg
 
    def parse_lfn2pfn(self,urlresults):
        """
        Parse the content of the result of lfn2pfn PhEDEx Data Service  call
 
        input:    DOM object with the content of the lfn2pfn call
        returns:  PFN  
        """
        result = urlresults.getElementsByTagName('phedex')
               
        if not result:
              return []
        result = result[0]
        pfn = None
        mapping = result.getElementsByTagName('mapping')
        for m in mapping:
            pfn=m.getAttribute("pfn")
            if pfn:
              return pfn
 
    def getStageoutPFN( self ):
        """
        input:   LFN,node name,protocol
        returns: PFN 
        """
        fullurl="%s/lfn2pfn?node=%s&lfn=%s&protocol=%s"%(self.datasvc_url,self.node,self.lfn,self.protocol) 
        domlfn2pfn = self.lfn2pfn()
        if not domlfn2pfn :
                msg="Unable to get info from %s"%fullurl
                raise RuntimeError, msg
  
        errormsg = self.parse_error(domlfn2pfn)
        if errormsg: 
                msg="Error extracting info from %s due to: %s"%(fullurl,errormsg)
                raise RuntimeError, msg
  
        stageoutpfn = self.parse_lfn2pfn(domlfn2pfn)
        if not stageoutpfn:
                msg ='Unable to get stageout path from TFC at Site %s \n'%self.node
                msg+='      Please alert the CompInfraSup group through their savannah %s \n'%self.FacOps_savannah
                msg+='      reporting: \n'
                msg+='       Summary: Unable to get user stageout from TFC at Site %s \n'%self.node
                msg+='       OriginalSubmission: stageout path is not retrieved from %s \n'%fullurl
                raise RuntimeError, msg

        return stageoutpfn 



if __name__ == '__main__':
  """
  Sort of unit testing to check Phedex API for whatever site and/or lfn.
  Usage:
     python PhEDExDatasvcInfo.py --node T2_IT_Bari --lfn /store/maremma [or --lfnFileList=filename ]

  """
  import getopt,sys,os,commands

  #lfn="/store/user/"
  #node='T2_IT_Bari'
  lfn = None
  node = None
  output = None
  lfnFileList = None

  usage="\n Usage: python CopyFile.py <options> \n Options: \n --lfn= \t\t  LFN \n --node=<URL> \t\t source node \n --lfnFileList= \t\t  filename containing a list of LFN \n --output = \t\t output path; a %s will be replaced with the lfn\n --help \t\t\t\t print this help \n"

  valid = ['node=','lfn=','lfnFileList=','output=']
  try:
       opts, args = getopt.getopt(sys.argv[1:], "", valid)
  except getopt.GetoptError, ex:
       print str(ex)
       sys.exit(1)
  for o, a in opts:
        if o == "--node":
            node = a
        if o == "--lfn":
            lfn = a
        if o == "--output":
            output = a
        if o == "--lfnFileList":
            lfnFileList = a

  if (lfn == None) and (lfnFileList == None) :
    print "\n either --lfn or --lfnFileList option has to be provided"
    print usage
    sys.exit(1)
  if (output == None):
    print "\n must specify output path with --output"
    print usage
    sys.exit(1)
  if (lfnFileList != None) and (output.find("%s") == -1):
    print "\n if using lfnFileList you must have a '%s' in the output"
    print usage
    sys.exit(1)
  if not node:
    print "use option --node to specify the site"
    print usage
    sys.exit(1)

##########################
#  real copy of a single file
##########################
  def copyLFN(alfn,anode):

   mycfg_params = { 'USER.storage_element': anode }
   dsvc = PhEDExDatasvcInfo(mycfg_params)
   dsvc.lfn = alfn
   srcPFN=dsvc.getStageoutPFN()
   print "SOURCE %s"%srcPFN
   destPFN=output
   if (output.find("%s") != -1):
       destPFN= output % (alfn,)
   print "DESTINATION %s"%destPFN
   #
   dest=commands.getoutput("dirname %s"%destPFN)
   print " Creating dir %s"%dest
   if not os.path.exists(dest):
      os.makedirs(dest)
   cpcmd="lcg-cp -v -b -D srmv2 %s file://%s"%(srcPFN,destPFN)
   print cpcmd
   #out = commands.getoutput(cpcmd)
   #print out
   os.system(cpcmd)
####################################33

  if (lfn != None):
    print "==> Copying file %s"%lfn
    copyLFN(lfn,node)

  if (lfnFileList != None) :
   print "==> Copying files from file : %s"%lfnFileList
   expand_lfnFileList=os.path.expandvars(os.path.expanduser(lfnFileList))
   if not os.path.exists(expand_lfnFileList):
    print "File not found: %s" % expand_lfnFileList
    sys.exit(1)
   lfnlist_file = open(expand_lfnFileList,'r')
   for line in lfnlist_file.readlines():
     lfn=line.strip()
     copyLFN(lfn,node) 
   lfnlist_file.close()


