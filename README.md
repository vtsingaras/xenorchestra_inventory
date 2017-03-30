### Install
This dynamic inventory script requires Python 3. It will **NOT** work with Python 2.

* Install required Python libraries
<pre># pip install pcre ipaddress xolib</pre>
* Move the files to the installation directory
<pre># mv xenorchestra.py /etc/ansible/xenorchestra.py
# mv xenorchestra.ini /etc/ansible/xeonrchestra.ini
# chmod +x /etc/ansible/xenorchestra.py
</pre>
* Edit xenorchestra.ini to your liking
* ???
* Profit!1!

### Usage
To use with ansible just specify the script as the inventory file.
<br>Example:
<pre>ansible -i /etc/ansible/xenorchestra.py -m ping all</pre>

<br>The inventory script reads its configuration from an ini file with the same name as the script next to the script.
<br>If you decide to place xenorchestra.py elsewhere you must make sure that there's an ini file next to it.

The script will read each VM's tags and make them into the corresponding ansible variables.
<br>With this you can do things like having as vm names non-resolvable names and overriding the ansible_host variable via a XenOrchestra tag:
<pre>ansible_host=172.16.1.1</pre>
<br>The script will try to autodetect the correct **_ansible\_host_** variable if there is no such tag by parsing all XenTools-reported IP addresses and using the first one that belongs to a management network.
<br>The **_management\_networks_** variable is defined the xenorchestra.ini file like so:
 <pre>management_networks = [ "172.16.0.0/16", "192.168.1.0/24" ]</pre>
 
You can also exclude VMs from being inventoried by setting the **_deny\_tags_** and/or **_deny\_regex_** variables like so:
<pre>
deny_tags = ["Disaster Recovery"]
deny_regex = ["^dev-.*"]
</pre>
This would exclude all VMs that have either the **Disaster Recovery** tag or their name starts with "**dev-**".

### Authentication

To use the script you must specify the XenOrchestra server's address:
<pre>host = xoa.example.com</pre>
and login credentials. You can either use email/password:
<pre>email = readeruser
password = readerpassword</pre>
or a token:
<pre>token = myreaderuserstokenthatigotusingtheapiorxocli</pre>

### Reporting bugs
Either open an issue or mail me at _vyronas **at** vtsingaras **dot** me_