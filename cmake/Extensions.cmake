# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


define_property(GLOBAL PROPERTY EXTENSION-OPTIONS
    BRIEF_DOCS "Global extension list"
    FULL_DOCS "Global extension list")

set_property(GLOBAL PROPERTY EXTENSION-OPTIONS "")

macro(register_extension extension-name)
	get_property(extensions GLOBAL PROPERTY EXTENSION-OPTIONS)
  set_property(GLOBAL APPEND PROPERTY EXTENSION-OPTIONS ${extension-name})
endmacro()

### TESTING MACROS

define_property(GLOBAL PROPERTY EXTENSION-TESTS
    BRIEF_DOCS "Global extension tests"
    FULL_DOCS "Global extension tests")

set_property(GLOBAL PROPERTY EXTENSION-TESTS "")

macro(register_extension_test extension-dir) 
  if (NOT SKIP_TESTS)
  	get_property(extensions GLOBAL PROPERTY EXTENSION-TESTS)
  	set_property(GLOBAL APPEND PROPERTY EXTENSION-TESTS "${extension-dir}")
  endif()
endmacro()

function(registerExtension extensionCondition dirName)
	if (NOT ${extensionCondition})
		add_subdirectory(${dirName})
	endif()
endfunction(registerExtension)

function(registerTest dirName)
	if (NOT SKIP_TESTS)
		add_subdirectory(${dirName})
	endif()
endfunction(registerTest)

### FUNCTION TO CREATE AN EXTENSION

function(createExtension extensionCondition extensionGuard extensionName description dirName)
   if (NOT ${extensionCondition})
		add_subdirectory(${dirName})
    	ADD_FEATURE_INFO("${extensionName}" ${extensionGuard} "${description}")
	    mark_as_advanced(${extensionGuard})
	    if (ARGV5)
	    	register_extension_test(${ARGV5})
	    endif(ARGV5)
	    if (ARGV6 AND ARGV7)
	    	if (${ARGV6})
				add_subdirectory(${ARGV7})	
			endif()
	    endif()
    endif()
endfunction(createExtension)

