'''
This file is part of picasa3meta.

picasa3meta is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

picasa3meta is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2012 Wayne Vosberg <wayne.vosberg@mindtunnel.com>
'''

import array
import os



class ThumbError(Exception):
    pass

class    MagicError(ThumbError):
    pass

class   ThumbIndexError(ThumbError):
    pass

class ThumbIndex(object):
    '''
    open the Picasa thumbindex.db file, verify the magic byte, and then read 
    all entries into name[], pathIndex[] arrays
        
    if a files has been removed from Picasa that thumbindex entry will not be 
    reused.  requesting that entry will return a null file/path name.  
    Requesting the index of a file that does not exist (or has been deleted)
    will return -1 (0xffffffff)
    
    usage: 
        from picasa3meta import thumbindex
        
        db = thumbindex.ThumbIndex("/path/to/Picasa3/db3/thumbindex.db")
        pmpIndex = db.indexOfFile("/full/path/to/Picasa3/image.jpg")
            (pmpIndex = integer, index of image.jpg data in Picasa3 
                        imagedata_xxx.pmp files)
        imageName = db.imageName(pmpIndex)
            (imageName = string, basename of image file / pmpIndex = integer, 
                        index of record in Picasa3 imagedata_xxx.pmp files)
        imagePath = db.imagePath(pmpIndex)
            (imagePath = string, path of image file / pmpIndex = integer, 
                        index of record in Picasa3 imagedata_xxx.pmp files)
        imageFullName = db.imageFullName(pmpIndex)
            (imageFullName = string, full path name of image file / 
                        pmpIndex = integer, index of record in Picasa3 
                        imagedata_xxx.pmp files)
      
    '''
    
    def __init__(self,thumbindex):
        '''
        open file "thumbindex", verify the magic byte, and then read all 
        entries into name[], pathIndex[] arrays
        
        '''
        
        self.header = array.array('I')
        self.entries = 0
        self.name = []
        self.pathIndex = array.array('I')
        
        self.inFile = open(thumbindex,"rb")
        self.header.fromfile(self.inFile,2)
                
        if self.header[0] != 0x40466666:
            raise MagicError("magic bytes %#x != 0x40466666"%self.header[0])
            
        self.entries = self.header[1]   # number of entries I expect to find
        
        self.index = 0
        self.name.append("")
        
        while True:
            # thumb entry begins with a null terminated string which gives 
            # the filename or pathname
            self.b = self.inFile.read(1)
            if len(self.b) == 0:    # EOF
                if self.index != self.entries:
                    raise ThumbIndexError(
                        "expected %d entries but only found %d"%
                        (self.entries,self.index))
                else:
                    return
            
            # file/path name will terminate with a null or 0xff char
            if self.b == chr(0xff) or self.b == chr(0):
                self.a = self.inFile.read(26)   # toss the next 26 bytes
                # the next int is the index into the names array of the 
                # path to this file or 0xffffffff if this is a directory
                self.pathIndex.fromfile(self.inFile,1)
                
                if len(self.name[self.index]) == 0:
                    # if there was no file name read then this file or 
                    # directory has been deleted.  Just set the path to 
                    # 0xffffffffff so we ignore it
                    self.pathIndex[self.index] = 0xffffffff
                self.index += 1
                self.name.append("")
            else:
                self.name[self.index] += self.b  # valid file/path name char
                
    
    def indexOfFile(self,findMe):
        '''
        find the index into the imagedata_xxx.pmp files for an image file.  
        Returns -1 if the image file is not found.
        
        usage:
        from picasa3meta import ThumbIndex
        
        db = ThumbIndex.ThumbIndex("/path/to/Picasa3/db3/thumbindex.db")
        index = db.indexOfFile("/full/path/to/image.jpg")
        
        '''
        
        self.findPath = os.path.dirname(findMe)+"/"
        self.findName = os.path.basename(findMe)
        
        for i in range(self.entries):
            if self.pathIndex[i] != 0xffffff:
                if self.name[i] == self.findName:
                    if self.name[self.pathIndex[i]] == self.findPath:
                        return i
            
        return -1
    
    def imagePath(self,what):
        '''       
        Find the path of the file at entry N.
        
        If entry N is a directory itself or is an image that has been removed,
        just return an empty string.  An exception will be thrown if you ask 
        for an entry > number of entries in thumbindex.db (self.entries)
        
        usage:
        from picasa3meta import thumbindex
        
        db = thumbindex.ThumbIndex("/path/to/Picasa3/db3/thumbindex.db")
        path = db.imagePath(5555)
        
        '''
        
        if self.pathIndex[what] == 0xffffffff:
            return ""
        else:
            return self.name[self.pathIndex[what]]
        
    def imageName(self,what):
        '''       
        Find the basename of the file at entry N.
        
        If entry N is a directory it will end with "/".  if the entry has been
        removed, return an empty string.  An exception will be thrown if you 
        ask for an entry > number of entries in thumbindex.db (self.entries)

        
        usage:
        from picasa3meta import thumbindex
        
        db = thumbindex.ThumbIndex("/path/to/Picasa3/db3/thumbindex.db")
        path = db.imageName(5555)
        
        '''
        
        return self.name[what]
    
    def imageFullName(self,what):
        '''     
        Find the full path name of the file/directory at entry N.
        
        If entry N is a directory it will end with "/".  if the entry has been
        removed, return an empty string.  An exception will be thrown if you 
        ask for an entry > number of entries in thumbindex.db (self.entries)

        
        usage:
        from picasa3meta import thumbindex
        
        db = thumbindex.ThumbIndex("/path/to/Picasa3/db3/thumbindex.db")
        path = db.imageFullName(5555)
        
        '''
        
        return os.path.join(self.imagePath(what),self.imageName(what))
    
    def dump(self,what):
        '''
        diagnostic dump of the entry at N
        
        '''
        
        if len(self.name[what]) > 0:          
            if self.pathIndex[what] == 0xffffffff:
                # must be dir
                return "entry["+str(what)+"]="+self.name[what]
            else:
                # must be file
                return "entry["+str(what)+"]="+ \
                    self.name[self.pathIndex[what]]+self.name[what]
        else:
            return "entry["+str(what)+"]= --deleted--"
    