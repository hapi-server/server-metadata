sudo cp serve-fs.plist /Library/LaunchDaemons
cd /Library/LaunchDaemons
sudo chown root:wheel serve-fs.plist
sudo chmod 0644 serve-fs.plist
sudo launchctl unload -w /Library/LaunchDaemons/serve-fs.plist
sudo launchctl load -w /Library/LaunchDaemons/serve-fs.plist

sudo launchctl stop serve-fs.plist
# Above does not stop service. Not sure why. Use
sudo pkill -f serve-fs.sh

sudo launchctl start serve-fs.plist
sleep 1
tail /var/log/system.log