"""This module contains the Function class, which is used to represent one function"""

class Function():
    def __init__(self, function_dict):
        self.function_dict = function_dict

    @property
    def name(self):
        return self.function_dict['name']
    
    @name.setter
    def name(self, value):
        self.function_dict['name'] = value

    @property
    def original_string(self):
        return self.function_dict['original_string']
    
    @original_string.setter
    def original_string(self, value):
        self.function_dict['original_string'] = value

    @property
    def relative_path(self):
        return self.function_dict['relative_path']
    
    @relative_path.setter
    def relative_path(self, value):
        self.function_dict['relative_path'] = value

    @property
    def docstring(self):
        return self.function_dict['docstring']
    
    @docstring.setter
    def docstring(self, value):
        self.function_dict['docstring'] = value

    @property
    def body(self):
        return self.function_dict['body']
    
    @body.setter
    def body(self, value):
        self.function_dict['body'] = value

    @property
    def signature(self):
        return self.function_dict['signature']
    
    @signature.setter
    def signature(self, value):
        self.function_dict['signature'] = value

    @property
    def start_line(self):
        return self.function_dict['start_point'][0]
    
    @start_line.setter
    def start_line(self, value):
        self.function_dict['start_point'][0] = value

    @property
    def end_line(self):
        return self.function_dict['end_point'][0]
    
    @end_line.setter
    def end_line(self, value):
        self.function_dict['end_point'][0] = value

    @property
    def syntax_pass(self):
        return self.function_dict['syntax_pass']

    @syntax_pass.setter
    def syntax_pass(self, value):
        self.function_dict['syntax_pass'] = value

    @property
    def class_info(self):
        return self.function_dict['class']
    
    @class_info.setter
    def class_info(self, value):
        self.function_dict['class'] = value
    
    def __str__(self):
        return str(self.function_dict)

