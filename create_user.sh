readonly username=${1:-"invitado"}
readonly password=${2:-"invitado"}
readonly auth_url=${3:-"http://localhost:10000/api/v4"}
readonly api_url=${4:-"http://localhost:5000/api/v2"}
readonly secret=${5:-"ed448c7a5449e9603058ce630e26c9e3befb2b15e3692411c001e0b4256852d2"}

echo "Creating user with username: $username and password: $password"

echo "\n"
echo "Creating scope 'jub' and assigning it to user '$username'"
echo "\n"
curl --request POST \
  --url $auth_url/scopes/ \
  --header 'Content-Type: application/json' \
  --data '{
  "name":"jub"
}'

echo "\n"
echo "Sign up user '$username'"
echo "\n"
curl --request POST \
  --url $api_url/users/signup \
  --header 'Content-Type: application/json' \
  --data '{
    "username":"'"$username"'",
    "first_name":"'"$username"'",
    "last_name":"'"$username"'",
    "email":"'"$username"'@example.com",
    "password":"'"$password"'",
    "profile_photo_url":"",
    "scope":"jub",
    "expiration": "1y"
  }'
