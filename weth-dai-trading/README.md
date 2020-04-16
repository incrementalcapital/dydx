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

## Timezones

Some of the longer scripts use Python's logging module. Configure the instance timezone to ensure that the date and time are properly recorded. For example:

```bash
sudo timedatectl set-timezone America/Mexico_City
```

## Updates

To make updates to the code, use the git. Specify a username and email:

```bash
git config --global user.email "incrementalcapital@gmail.com"
git config --global user.name "incremental capital"
```

## Messaging

Install the boto3 Python library for AWS to receive alerts. Configure the test with a valid mobile number and check that messaging works:

```bash
pip3 install boto3
vi testsms.py
py testsms.py
```

## Reporting

To use MongoDB to facilitate gathering information on the performance of trades executed:

1. Rename the example-dbconnection.py file to dbconnection.py.
2. Edit that file configuration to provide an alias/identifier for the dYdX account.
3. Add the credentials and connection string to the mongodb server.
4. Install pymongo and dnspython using pip3.

```bash
mv example-dbconnection.py dbconnection.py
vi dbconnection.py
pip3 install pymongo
pip3 install dnspython
```

**Note:** If you get SSL errors when attempting to create a collection on Mac OS, you may need to append the following to your *dbclient* connection string in the **dbconnection.py** file:

```bash
ssl=true&ssl_cert_reqs=CERT_NONE
```

For example, if you see:

```bash
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

Then be sure to specify that SSL certificates are not required (i.e. **ssl_cert_reqs=CERT_NONE**).

An even better solution is to install a certificate authority (CA) bundle using before attempting to access mongodb on Atlas:

```bash
open "/Applications/Python 3.6/Install Certificates.command"
```
