# This generates the Protobuf libraries from source.

# All html files depend on their respective txt files.
py_files := $(patsubst %.proto,%_pb2.py,$(wildcard *.proto))

proto_files := $(wildcard *.proto)

# Make all python files from any proto files found here.
all: $(py_files)

%_pb2.py: %.proto
	protoc --python_out=. --proto_path=. --proto_path=../.. \
        --proto_path=/usr/include --proto_path=/usr/local/include \
        --proto_path=..\\.. --proto_path=c:\\grr_build\\protobuf\\src $(<F)


.PHONY: sync clean
clean:
	rm *_pb2.py

