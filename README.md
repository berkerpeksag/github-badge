# Github Badge

[GitHub Badge][ghb] is a simple embeddable badge showing your [GitHub][github] stats
like the number of public repositories, number of followers, favorite languages etc.

[github]: http://github.com
[ghb]: http://githubbadge.appspot.com/

## Please note

We do rely on heavy caching, so give it about 24 to 48 hours to pick up any changes.

## Authors

* [Berker Peksag](https://github.com/berkerpeksag)
* [Burak Yiğit Kaya](https://github.com/BYK)

## Contributors

* [Bruno Lara Tavares](https://github.com/bltavares)
* [Mathias Bynens](https://github.com/mathiasbynens)
* [Emre Sevinc](https://github.com/emres)
* [Samet Atdag](https://github.com/samet)
* [Christian Ketterer](https://github.com/cketti)

## Installation

### Local development

1. Follow the instructions at the [Google Cloud SDK for Python](https://cloud.google.com/appengine/docs/standard/python/download)
   page to install it.

2. Create a *development* configuration to use your GitHub credentials for testing:

   ```sh
   $ cp app/config/development.sample.py app/config/development.py
   ```

3. Start the development server:

   ```sh
   $ dev_appserver.py -A githubbadge app.yaml
   ```

### Production

1. Create a *googleappengine* configuration and use the credentials from the
   [OAuth application](https://github.com/settings/developers) you've created on
   GitHub:

   ```sh
   $ cp app/config/googleappengine.sample.py app/config/googleappengine.py
   ```

2. Then run the following command to start deployment:

   ```sh
   $ gcloud app deploy --version 2 app.yaml
   ```

## License

All files that are part of this project are covered by the following license,
except where explicitly noted.

> This Source Code Form is subject to the terms of the Mozilla Public
> License, v. 2.0. If a copy of the MPL was not distributed with this
> file, You can obtain one at http://mozilla.org/MPL/2.0/.
