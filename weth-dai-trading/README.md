# dYdX Scripts

## Installation

To get these scripts working:

1. Login to the AWS console, fire up an EC2 instance, and secure shell it to the instance.
2. Make sure you have python3 installed.
3. Clone this repository.
4. Prepare your wallet credentials by moving the example module (example-credentials.py) to credentials.py.
5. Use vi to edit the credentials.py module and add the private key of your wallet.
6. Get PIP if it is not present.
7. Download dYdX's Python stuff.

Essentially, these steps would look something like this:

```bash
sudo apt update # update apt
python3 --version # confirm that python3 is installed (it is by default on Ubuntu Server 18.04 LTS)
git clone https://github.com/munair/dydx.git # download repository
mv example-credentials.py credentials.py # prepare credentials
vi credentials.py # insert private key
pip3 --version || sudo apt install python3-pip -y # check for pip3 and install it if not found
pip3 install dydx-python # install dydx libraries
```

## Usage

To use these scripts, type python3 before the script name.
[If you don't want to see the __pycache__ directory, you can create an alias.]

For example:

```bash
alias py='python3 -B'
py long-eth-perpetually.py
```

**Note:** for best performance, suppressing the creation of Python's cache directory (__pycache__) is *not* recommended.

## Updates

To make updates to the code, use the git. Specify a username and email:

```
git config --global user.email "incrementalcapital@gmail.com"
git config --global user.name "incremental capital"
```
