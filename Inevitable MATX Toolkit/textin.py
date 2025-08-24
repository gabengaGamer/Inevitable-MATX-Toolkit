#=============================================================================
#
# Module:  Inevitable .txt input parser. Based on TextIN.cpp
#
#=============================================================================

import re
import os
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union

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
        
        for char in type_chars:
            data_type = TextType.from_char(char)
            self.types.append(data_type)
    
    def parse_value(self, values: List[str]) -> List[Any]:
        result = []
        for i, (value, data_type) in enumerate(zip(values, self.types)):
            if data_type == TextType.INTEGER:
                result.append(int(value))
            elif data_type == TextType.FLOAT:
                result.append(float(value))
            elif data_type == TextType.STRING:
                if value.startswith('"') and value.endswith('"'):
                    result.append(value[1:-1])
                else:
                    result.append(value)
            elif data_type == TextType.GUID:
                result.append(value)             
        return result   

#=============================================================================

class TextSection:
    def __init__(self, name: str, count: Optional[int] = None):
        self.name = name
        self.count = count
        self.fields = []
        self.data = []
    
    def add_field(self, field: TextField):
        self.fields.append(field)
    
    def add_data_row(self, row: List[Any]):
        if len(row) != len(self.fields):
            raise ValueError(f"Count elements in row ({len(row)}) not match fields count ({len(self.fields)}). Aborting!")      
        self.data.append(row)

#=============================================================================

class TextParser: 
    def __init__(self):
        self.sections = {}
        self.filepath = None
    
    def parse_file(self, filepath: str) -> Dict[str, TextSection]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}. Aborting!")
            
        self.filepath = filepath
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        sections = {}
        current_section = None
        current_content = ""
        
        lines = content.split('\n')
        i = 0
        in_quotes = False
        
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            if not line:
                continue
            
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
            
            if not in_quotes and line.startswith('[') and ']' in line:
                if current_section:
                    self.parse_section(current_section[0], current_section[1], current_content)
                    current_content = ""
                
                section_header = line[1:line.index(']')]
                parts = section_header.split(':')
                
                name = parts[0].strip()
                count_str = parts[1].strip() if len(parts) > 1 else None
                
                current_section = (name, count_str)
            else:
                if current_section:
                    current_content += line + "\n"
        
        if current_section:
            self.parse_section(current_section[0], current_section[1], current_content)
        
        return self.sections
    
    def parse_section(self, name: str, count_str: str, section_content: str):
        count = int(count_str) if count_str else None
        section = TextSection(name, count)
        
        fields_pattern = r'{\s*(.*?)\s*}'
        fields_match = re.search(fields_pattern, section_content, re.DOTALL)
        
        if fields_match:
            fields_raw = fields_match.group(1).strip()
            
            i = 0
            while i < len(fields_raw):
                while i < len(fields_raw) and (fields_raw[i].isspace() or fields_raw[i] in ','):
                    i += 1
                
                if i >= len(fields_raw):
                    break
                
                field_name = ""
                while i < len(fields_raw) and fields_raw[i] != ':':
                    field_name += fields_raw[i]
                    i += 1
                
                field_name = field_name.strip()
                
                if i < len(fields_raw) and fields_raw[i] == ':':
                    i += 1
                else:
                    raise ValueError(f"Not found splitter ':' after row name '{field_name}'. Aborting!")
                
                field_type = ""
                while i < len(fields_raw) and fields_raw[i].isalpha():
                    field_type += fields_raw[i]
                    i += 1
                
                valid_types = {'d', 'D', 'f', 'F', 's', 'S', 'g', 'G'}
                for char in field_type:
                    if char not in valid_types:
                        raise ValueError(f"Unexpected dimension '{char}' in row '{field_name}'. Aborting!")
                
                if field_name and field_type:
                    field = TextField(field_name, field_type)
                    section.add_field(field)
        
        lines = []
        is_commentary = False
        for line in section_content.split('\n'):
            line_stripped = line.strip()
            
            if '/*' in line_stripped and not is_commentary:
                is_commentary = True
                parts = line_stripped.split('/*', 1)
                if parts[0].strip() and not parts[0].strip().startswith('//'):
                    lines.append(parts[0].strip())
                continue
            
            if '*/' in line_stripped and is_commentary:
                is_commentary = False               
                parts = line_stripped.split('*/', 1)
                if len(parts) > 1 and parts[1].strip() and not parts[1].strip().startswith('//'):
                    lines.append(parts[1].strip())
                continue
            
            if is_commentary:
                continue
            
            if line_stripped and not line_stripped.startswith('//'):
                lines.append(line_stripped)
                
        data_lines = [line for line in lines if not (line.startswith('{') or line.startswith('-'))]
                    
        field_value_counts = []
        for field in section.fields:
            field_value_counts.append(len(field.types))
        
        for line in data_lines:
            line = line.strip()
            if not line:
                continue
            
            values = []
            current = ""
            in_quotes = False
            
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                    current += char
                elif char.isspace() and not in_quotes:
                    if current:
                        values.append(current)
                        current = ""
                else:
                    current += char
            
            if current:
                values.append(current)
            
            parsed_row = []
            value_index = 0
            
            for i, field in enumerate(section.fields):
                num_values = field_value_counts[i]                
                if value_index + num_values <= len(values):
                    field_values = values[value_index:value_index + num_values]                    
                    try:
                        converted = field.parse_value(field_values)                       
                        if len(converted) == 1:
                            parsed_row.append(converted[0])
                        else:
                            parsed_row.append(converted)                        
                    except ValueError as e:
                        raise ValueError(f"Error processing field '{field.name}' with values {field_values}: {e}")                  
                    value_index += num_values
                else:
                    raise ValueError(f"Unexpected dimension in field '{field.name}'. Expected {num_values} value, but found {len(values) - value_index}. Aborting!")
            
            section.add_data_row(parsed_row)       
        
        if count is not None and len(section.data) != count:
            raise ValueError(f"Unexpected dimension in section [{name}]. Expected {count} rows, but found {len(section.data)}. Aborting!")    
        
        self.sections[name] = section
        
#=============================================================================        