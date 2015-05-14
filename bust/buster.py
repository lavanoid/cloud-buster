from cloudflarenetwork import CloudFlareNetwork
from descriptor.mxrecords import MxRecords
from descriptor.pagetitle import PageTitle
from target import Target
from panels import PANELS


class CloudBuster:

    def __init__(self, domain):
        self.domain = domain
        self.targets = {
            'main': None,
            'subdomains': [],
            'panels': [],
            'mxs': []
        }
        self.crimeflare_ip = None

    def resolving(self):
        if self.targets['main']:
            if self.targets['main'].ip:
                return True

        return False

    def check_ip(self, ip):
        net = CloudFlareNetwork()
        print(net.in_range(ip))

    def scan_main(self):
        target = Target(self.domain, 'target')
        target.print_infos()
        self.targets['main'] = target

    def protected(self):
        if not self.targets['main'] or type(self.targets['main']) != Target:
            return False

        return self.targets['main'].protected

    def scan_subdomains(self, subdomains=None):
        if subdomains:
            toscan = subdomains
        else:
            toscan = open('lists/subdomains').read().splitlines()

        subTargets = [
            Target(sub+'.'+self.domain, 'subdomain', timeout=5)
            for sub in toscan
        ]

        for target in subTargets:
            target.print_infos()
            self.targets['subdomains'].append(target)

    def scan_panels(self, panels=None):

        for panel in PANELS:
            if not panels or panel['name'] in panels:
                target = Target(
                    domain=self.domain,
                    name=panel['name']+':'+str(panel['port']),
                    port=panel['port'],
                    timeout=2,
                    ssl=panel['ssl']

                )
                target.print_infos()
                self.targets['panels'].append(target)

    def search_crimeflare(self):
        for line in open('lists/ipout'):
            if self.domain in line:
                self.crimeflare_ip = line.partition(' ')[2].rstrip()
                return

    def scan_mx_records(self):

        mxs = MxRecords(self.domain).__get__()
        if not mxs:
            return

        for mx in mxs:
            target = Target(mx, 'mx', timeout=1)
            target.print_infos()
            self.targets['mxs'].append(target)

    def print_infos(self):
        print('[SCAN SUMARY]')

        if self.targets['main']:
            print('Target: '+self.targets['main'].domain)
            print('> ip: '+str(self.targets['main'].ip))
            print('> protected: '+str(self.targets['main'].protected))

        print('[found ips]')

        for host in self.list_interesting_hosts():
            print(host['ip']+' > '+host['description'])

    def match_results(self):
        print('[analysing results]')

        if not self.targets['main'].protected:
            print('>> NOT BEHIND CLOUDFLARE <<')
            return

        target_title = PageTitle(
            'http://'+self.targets['main'].domain
        ).__get__()
        print('target title > '+str(target_title))

        if target_title:
            prev_ip = None

            for host in self.list_interesting_hosts():
                if prev_ip != host['ip']:
                    print('scanning > '+host['ip'])
                    prev_ip = host['ip']

                    title = PageTitle(
                        'http://'+host['ip'],
                        self.targets['main'].domain
                    ).__get__()

                    if title == target_title:
                        print('>> CONFIRMED <<')
                        print('> ip: '+host['ip'])
                        print('> title: '+str(title))
                        return

        print('>> UNABLE TO CONFIRM <<')

    def list_interesting_hosts(self):
        hosts = []
        targets = self.targets['subdomains'] \
            + self.targets['panels'] \
            + self.targets['mxs']

        for target in targets:
            if target.ip and not target.protected \
                    and target.status and target.status != 400:
                hosts.append({
                    'ip': target.ip,
                    'description': target.domain+' / '+target.name
                })

        if self.crimeflare_ip:
            hosts.append({
                'ip': self.crimeflare_ip,
                'description': self.targets['main'].domain
                + ' / from crimeflare.com db'
            })

        return hosts
