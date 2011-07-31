"""
 js_function_slimmer.py
 Peter Bengtsson, mail@peterbe.com, 2004-2006
 
 >>> from slimmer.js_function_slimmer import slim
 >>> print slim('''// comment
 ... function foo(parameter1, parameter2) {
 ...    if (parameter1 > parameter2) {
 ...        parameter2 = parameter1;
 ...    }   
 ... }
 ... // post comment''')
 // comment
 function foo(_0,_1) {
     if (_0 > _1) {
         _1 = _0;
     }   
 }
 // post comment
 >>>
 
 It digs out the functions and make them slimmer.
                   
Changes::
 0.0.2      May 2006    Added slim_func_names()
 
 0.0.1      Feb 2006    First draft
 

"""
import re



function_start_regex = re.compile('(function[ \w+\s*]\(([^\)]*)\)\s*{)')
function_start_regex = re.compile('(function(\s+\w+|)\s*\(([^\)]*)\)\s*{)')

function_name_regex = re.compile('(function (\w+)\()')

def _findFunctions(whole):
    functions = []
    for res in function_start_regex.findall(whole):
        function_start, function_name, params = res
        params_split = [x.strip() for x in params.split(',')]
        stack = 1
        code = function_start
        core_code = ''
        start = whole.find(function_start) + len(code)
        while stack > 0:
            #start += 1
            next_char = whole[start]
            core_code += next_char
            if next_char == '{':
                stack += 1
            elif next_char == '}':
                stack -= 1
            start += 1
        
        yield (params, 
               params_split, 
               core_code[:-1], 
               function_start)
        

def slim_params(code):
    new_functions = []
    old_functions = {}
    new_code = code
    for params, params_split, core, function_start in _findFunctions(code):
        params_split_use = [x for x in params_split if len(x)>1]
        _param_regex = '|'.join([r'\b%s\b' % x for x in params_split_use])
        param_regex = re.compile(_param_regex)
        new_params = {}
        for i in range(len(params_split_use)):
            new_params[params_split[i]] = '_%s' % i
            
        def replacer(match):
            return new_params.get(match.group())
        
        new_core = param_regex.sub(replacer, core)
        
        _params = []
        for p in params_split:
            _params.append(new_params.get(p,p))
        
        
        new_function = function_start.replace(params, ','.join(_params))+\
                       new_core + '}'
        
        old_function = function_start+core+'}'
        old_functions[old_function] = new_function
        
    # killer regex
    regex = '|'.join([re.escape(x) for x in old_functions.keys()])
    def replacer(match):
        return old_functions.get(match.group())
    return re.sub(regex, replacer, new_code)


class NamesGenerator:
    def __init__(self):
        self.i = 0
        self.pool = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        
    def next(self):
        try:
            e = self.pool[self.i]
            self.i = self.i + 1
        except IndexError:
            if not hasattr(self, 'j'):
                self.j = 0
                self.pool.extend([x.lower() for x in self.pool])
            try:
                e = self.pool[self.i % len(self.pool)] +\
                    self.pool[self.j]
                self.j = self.j + 1
            except IndexError:
                self.i += 1
                self.j = 0
                return self.next()
        
        return '_%s' % e

def slim_func_names(js):
    relabel_functions = []
    functions = function_name_regex.findall(js)
    new_names_generator = NamesGenerator()
    for whole_func, func_name in functions:
        count = js.count(func_name)
        if len(func_name) > 2 and count > 1:
            #print func_name, count, 
            #len(re.findall(r'\b%s\b'% re.escape(func_name), js))
            new_name = new_names_generator.next()
            if re.findall(r'\b%s\b' % re.escape(new_name), js):
                #print  "new_name:%r\n\n%s" % (new_name, js)
                continue
            js = re.sub(r'\b%s\b'% re.escape(func_name), new_name, js)
            relabel_functions.append((func_name, new_name))
    add_codes=['var %s=%s'%(x,y) for (x,y) in relabel_functions]
    add_code = ';'.join(add_codes)
    
    return js + add_code
        
    
            
            
            
def slim(code):
    return slim_func_names(slim_params(code))

def test(inputbuffer):
    from time import time

    t0 = time()
    
    js1 = inputbuffer.read()
    res = slim(js1)
    t1 = time()
    print t1-t0
    return res
    
if __name__=='__main__':
    import sys
    argv = sys.argv[1:]
    if argv:
        print test(open(argv[0]))
    else:
        test(sys.stdin)

