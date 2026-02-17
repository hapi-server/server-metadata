
sudo cp $1.plist /Library/LaunchDaemons
sudo chown root:wheel /Library/LaunchDaemons/$1.plist
sudo chmod 0644 $1.plist
sudo launchctl unload -w /Library/LaunchDaemons/$1.plist
sudo launchctl load -w /Library/LaunchDaemons/$1.plist

sudo launchctl stop $1.plist
# Above does not always stop service. Not sure why. Use
#sudo pkill -f $1.sh

rm -f ../data/log/$1/stdout
rm -f ../data/log/$1/stderr

sudo launchctl start $1.plist

sleep 2
tail ../data/log/$1/stdout
tail ../data/log/$1/stderr
