# Makefile for building GRR linux clients in vagrant VMs

# TODO: This is Makefile is temporary, replace with changes to python build
# code.  Also create packages in timestamped directories

src_dir = .
build_dir = /usr/local/grr_build
client_build_linux = PYTHONPATH=. python grr/client/client_build.py --platform=linux --allow_missing_config_definitions
amd64 = --arch=amd64
i386 = --arch=i386

test:
	cd $(build_dir); PYTHONPATH=. python grr/run_tests.py

%_installer_linux_64: %_build_linux_64
	cd $(build_dir); . ~/PYTHON_ENV/bin/activate; $(client_build_linux) $(amd64) --config=/grr/config/$*.yaml deploy;

%_build_linux_64:
	cd $(build_dir); . ~/PYTHON_ENV/bin/activate; $(client_build_linux) $(amd64) --config=/grr/config/$*.yaml build

setup:
	sudo mkdir -p $(build_dir); \
	sudo chown vagrant $(build_dir); \
	sudo apt-get install git-cvs; \
	git clone https://github.com/pyinstaller/pyinstaller.git $(build_dir)/pyinstaller; \
	git clone https://github.com/google/grr.git $(build_dir)/grr; \
	cd $(build_dir)/grr/proto; \
	make; \
	cd ../artifacts; \
	make
