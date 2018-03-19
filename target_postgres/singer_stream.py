from copy import deepcopy

from jsonschema import Draft4Validator, FormatChecker

from target_postgres.pysize import get_size

SINGER_RECEIVED_AT = '_sdc_received_at'
SINGER_BATCHED_AT = '_sdc_batched_at'
SINGER_SEQUENCE = '_sdc_sequence'
SINGER_TABLE_VERSION = '_sdc_table_version'
SINGER_PK = '_sdc_primary_key'
SINGER_SOURCE_PK_PREFIX = '_sdc_source_key_'
SINGER_LEVEL = '_sdc_level_{}_id'

class BufferedSingerStream(object):
    def __init__(self,
                 stream,
                 schema,
                 key_properties,
                 *args,
                 max_rows=200000,
                 max_buffer_size=104857600, # 100MB
                 **kwargs):
        self.update_schema(schema, key_properties)
        self.stream = stream
        self.max_rows = max_rows
        self.max_buffer_size = max_buffer_size

        self.__buffer = []
        self.__size = 0

    def update_schema(self, schema, key_properties):
        original_schema = deepcopy(schema)

        ## TODO: mark schema dirty here for caching in PostgresTarget?

        ## TODO: validate against stricter contraints for this target?
        self.validator = Draft4Validator(original_schema, format_checker=FormatChecker())

        if len(key_properties) == 0:
            self.use_uuid_pk = True
            key_properties = [SINGER_PK]
            schema['properties'][SINGER_PK] = {
                'type': 'string'
            }
        else:
            self.use_uuid_pk = False

        self.schema = schema
        self.original_schema = original_schema
        self.key_properties = key_properties

    @property
    def buffer_full(self):
        ln = len(self.__buffer)
        if ln >= self.max_rows:
            return True

        if ln > 0:
            if self.__size >= self.max_buffer_size:
                return True

        return False

    def add_record(self, record):
        self.validator.validate(record)
        self.__buffer.append(record)
        self.__size += get_size(record)

    def peek_buffer(self):
        return self.__buffer

    def flush_buffer(self):
        _buffer = self.__buffer
        self.__buffer = []
        self.__size = 0
        return _buffer
