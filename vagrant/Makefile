# Makefile for building GRR linux clients in vagrant VMs

all:
	screen -c buildanddeploy_screenrc

templates:
	screen -c build_screenrc

vmclean:
	screen -c reprovision_screenrc

windows_templates:
	./build_templates.sh windows_7_64

centos_5.11_32:
	./build_and_deploy.sh centos_5.11_32

centos_5.11_64:
	./build_and_deploy.sh centos_5.11_64

ubuntu_lucid32:
	./build_and_deploy.sh ubuntu_lucid32

ubuntu_lucid64:
	./build_and_deploy.sh ubuntu_lucid64

OS_X_10.8.5:
	./build_and_deploy.sh OS_X_10.8.5

windows_7_64:
	./build_and_deploy.sh windows_7_64

