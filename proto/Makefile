# This generates the Protobuf libraries from source.

# All .py files depend on their respective .proto files.
py_files := $(patsubst %.proto,%_pb2.py,$(wildcard *.proto))

proto_files := $(wildcard *.proto)

PROTOC=protoc

PROTOPATH=--proto_path=.

ifeq ($(OS),Windows_NT)
  PROTOPATH += --proto_path=..\\.. --proto_path=c:\\grr_build\\protobuf\\src
else
  PROTOPATH += --proto_path=../.. --proto_path=/usr/include
  PROTOPATH += --proto_path=/usr/local/include
endif

# Make all python files from any proto files found here.
all: $(py_files)

%_pb2.py: %.proto
	$(PROTOC) --python_out=. $(PROTOPATH) $(<F)


.PHONY: sync clean
clean:
	rm *_pb2.py

