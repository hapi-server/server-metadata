sudo cp serve-table.plist /Library/LaunchDaemons
cd /Library/LaunchDaemons
sudo chown root:wheel serve-table.plist
sudo chmod 0644 serve-table.plist
sudo launchctl unload -w /Library/LaunchDaemons/serve-table.plist
sudo launchctl load -w /Library/LaunchDaemons/serve-table.plist

sudo launchctl stop serve-table.plist
# Above does not stop service. Not sure why. Use
sudo pkill -f serve-table.sh

sudo launchctl start serve-table.plist
sleep 1
tail /var/log/system.log