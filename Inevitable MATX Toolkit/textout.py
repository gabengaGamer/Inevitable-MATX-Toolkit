#=============================================================================
#
# Module:  Inevitable .txt output parser. Based on TextOUT.cpp
#
#=============================================================================

import os
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum

#=============================================================================

class TextType(Enum):
    INTEGER = 'D'
    FLOAT   = 'F'
    STRING  = 'S'
    GUID    = 'G'
    
    @classmethod
    def from_char(cls, char: str) -> 'TextType':
        char = char.upper()
        for type_enum in cls:
            if char == type_enum.value:
                return type_enum

#=============================================================================

class TextField:
    def __init__(self, name: str, type_chars: str):
        self.name = name
        self.type_chars = type_chars
        self.types = []
        self.total_space = []
        self.has_negative = []
        self.full_spec = f"{name}:{type_chars}"
        self.type_widths = []
        self.total_width = 0
        
        for char in type_chars:
            data_type = TextType.from_char(char)
            self.types.append(data_type)
            self.total_space.append(0)
            self.has_negative.append(False)

#=============================================================================

class TypeEntry:
    def __init__(self):
        self.offset = 0
        self.length = 0
        self.field_index = 0
        self.type_index = 0
        self.back_offset = 0
        self.is_digit = False
        self.value = ""

#=============================================================================

class TextWriter:
    def __init__(self):
        self.fp = None
        self.fields = []
        self.block_name = ""
        self.line_count = 0
        self.current_line = 0
        self.current_field = 0
        self.num_fields = 0
        self.type_entries = []
        self.block_data = ""
    
    def open_file(self, filepath: str) -> None:
        try:
            self.fp = open(filepath, 'w', encoding='utf-8')
        except IOError:
            raise IOError(f"Unable to open {filepath} for saving")
    
    def close_file(self) -> None:
        if self.fp:
            self.fp.close()
            self.fp = None
    
    def __del__(self):
        if hasattr(self, 'fp') and self.fp:
            self.close_file()
    
    def add_header(self, header_name: str, count: int = -1) -> None:
        
        self.line_count = 1 if count < 0 else count
        self.current_line = 0
        self.current_field = 0
        self.num_fields = 0
        self.type_entries = []
        self.fields = []
        self.block_data = ""
        
        if count < 0:
            self.block_name = f"[ {header_name} ]\n"
        else:
            self.block_name = f"[ {header_name} : {count} ]\n"
        
        if count == 0:
            self.add_end_line()    
    
    def add_field(self, field_spec: str, *values) -> None:
        
        assert self.current_line < self.line_count, "Too many lines added"
        
        field_specs = field_spec.split()
        
        expected_values = 0
        for spec in field_specs:
            if ":" not in spec:
                raise ValueError(f"Field specification must include types (e.g. 'name:dfs'): {spec}")
            name, type_chars = spec.split(":", 1)
            expected_values += len(type_chars)
        
        if len(values) != expected_values:
            raise ValueError(f"Expected {expected_values} values for field {field_spec}, got {len(values)}")
        
        value_index = 0
        orig_current_field = self.current_field
        
        for i, spec in enumerate(field_specs):
            name, type_chars = spec.split(":", 1)
            
            if self.current_line == 0:            
                field = TextField(name, type_chars)
                self.fields.append(field)
                self.num_fields += 1
            else:
                current_field_index = orig_current_field + i
                if current_field_index >= len(self.fields):
                    raise ValueError(f"Field index out of range: {current_field_index}, fields: {len(self.fields)}")
                
                field = self.fields[current_field_index]
                if field.name != name:
                    raise ValueError(f"Field name mismatch: expected {field.name}, got {name}")
            
            field_values = values[value_index:value_index + len(type_chars)]
            value_index += len(type_chars)
            
            if len(field_values) != len(field.types):
                raise ValueError(f"Expected {len(field.types)} values for field {name}, got {len(field_values)}")
            
            for j, (value, data_type) in enumerate(zip(field_values, field.types)):
                entry = TypeEntry()
                entry.field_index = orig_current_field + i
                entry.type_index = j
                entry.back_offset = 0
                
                if data_type == TextType.INTEGER:
                    entry.value = f"{value}"
                    entry.is_digit = True
                    if value < 0:
                        field.has_negative[j] = True
                elif data_type == TextType.FLOAT:
                    if isinstance(value, (float, int)):
                        entry.value = f"{float(value):.6f}"
                    else:
                        entry.value = f"{value}"
                    entry.is_digit = True
                    if float(value) < 0:
                        field.has_negative[j] = True
                elif data_type == TextType.STRING:
                    entry.value = f'"{value}"'
                    entry.is_digit = False
                elif data_type == TextType.GUID:
                    if isinstance(value, str):
                        entry.value = f'"{value}"'
                    else:
                        high = (value >> 32) & 0xFFFFFFFF
                        low = value & 0xFFFFFFFF
                        entry.value = f'"{high:08X}:{low:08X}"'
                    entry.is_digit = False
                
                entry.length = len(entry.value)
                entry.offset = len(self.block_data)
                self.block_data += entry.value
                
                base_width = entry.length
                
                if entry.is_digit and entry.value[0] != '-' and field.has_negative[j]:
                    base_width += 1               
                        
                if field.total_space[j] < base_width:
                    field.total_space[j] = base_width
                
                self.type_entries.append(entry)
        
        self.current_field += len(field_specs)
        
    def add_end_line(self) -> None:
        self.current_line += 1
        self.current_field = 0
        
        if self.line_count == 0 or self.current_line == self.line_count:
            self.fp.write(self.block_name)
        
            header_fields = []
            separator_parts = []
            
            for field in self.fields:
                type_widths = []
                for i, type_size in enumerate(field.total_space):
                    padded_width = max(type_size, 1)
                    type_widths.append(padded_width)
                
                total_width = sum(type_widths) + len(type_widths) - 1
                
                header_len = len(field.full_spec)
                if total_width < header_len:
                    diff = header_len - total_width
                    type_widths[-1] += diff
                    total_width = header_len
                
                field.type_widths = type_widths
                field.total_width = total_width
                
                header_fields.append(field.full_spec + " " * (total_width - header_len))
                
                separator_parts.append("-" * total_width)
            
            self.fp.write(f" {{ {' '.join(header_fields)} }}\n")
            self.fp.write(f"// {' '.join(separator_parts)} \n")
            
            entry_index = 0
            for line_idx in range(self.line_count):
                self.fp.write("   ")
                
                for field_idx, field in enumerate(self.fields):
                    field_str = ""
                    current_width = 0
                    
                    for type_idx, type_width in enumerate(field.type_widths):
                        entry = self.type_entries[entry_index]
                        entry_index += 1
                        
                        prefix = ""
                        if entry.is_digit and field.has_negative[type_idx] and entry.value[0] != '-':
                            prefix = " "
                        
                        value_str = prefix + entry.value
                        field_str += value_str
                        current_width += len(value_str)
                        
                        if type_idx < len(field.type_widths) - 1:
                            padding = type_width - len(value_str)
                            if padding > 0:
                                field_str += " " * padding
                            current_width += padding + 1
                            field_str += " " 
                    
                    if current_width < field.total_width:
                        field_str += " " * (field.total_width - current_width)
                    
                    self.fp.write(field_str)
                    
                    if field_idx < len(self.fields) - 1:
                        self.fp.write(" ")
                
                self.fp.write("\n")
                
                if (line_idx + 1) % 80 == 0 and (self.line_count - line_idx) > 10:
                    self.fp.write(f"// {' '.join(separator_parts)} \n")
                    headers = []
                    for field in self.fields:
                        header = field.full_spec + " " * (field.total_width - len(field.full_spec))
                        headers.append(header)                
                    self.fp.write(f"// {' '.join(headers)}\n")
                    self.fp.write(f"// {' '.join(separator_parts)} \n")
            
            self.fp.write("\n")         
            
#=============================================================================            