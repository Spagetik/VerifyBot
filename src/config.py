bot_token = "token"  # Your bot token
command_prefix = ">>"  # Your bot command prefix
guild_id = 0  # Guild id where bot will verify users
common_role_id = 0  # Role id which will be added to verified users
error_message = "This code doesn't exist! Use **`/verify`** on server to get new one!"  # Message for user when verify error occurred
success_message = "You successfully verified!"  # Message for user when user successfully verified
ban_message = "You was banned!"  # Message for banned users, when they try to verify from new Discord account
move_message = "{old}, you verified from new account - {new}." \
               "\n\n**If you don't move your account, text server administrator!**"  # Migration message when user migrate to new Discord account

database_host = 'localhost'  # Database host
database_port = 3306  # Database host port
database_name = 'dis_verify'  # Database name
database_user = 'DisVerify'  # User that have access to database
database_password = 'qwerty'  # User password
