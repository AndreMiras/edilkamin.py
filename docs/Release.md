# How to release

This is documenting the release & deployment process.

We're using [semantic versioning](https://semver.org/) where `major.minor.patch` should be set accordingly.

```sh
VERSION=major.minor.patch
```

## Start the release

```sh
git checkout -b release/$VERSION
```

Now update the [pyproject.toml](../pyproject.toml) `version` to match the new release version.

```sh
sed --regexp-extended 's/version = "(.+)"/version = "'$VERSION'"/' --in-place pyproject.toml
```

Then commit/push and create a pull request targeting the `main` branch.

```sh
git commit -a -m ":bookmark: $VERSION"
git push origin release/$VERSION
```

Once the pull requests is approved/merged, tag the `main` branch with the version.
In the case of a sole owner, no pull request is required, but at least verify the CI builds green.

```sh
git checkout main
git pull
git tag -a $VERSION -m ":bookmark: $VERSION"
git push --tags
```

## Publish to PyPI

This process is handled automatically by [GitHub Actions](https://github.com/AndreMiras/edilkamin.py/actions/workflows/pypi-release.yml).
If needed below are the instructions to perform it manually.
Build it:

```sh
make release/build
```

Check archive content:

```sh
tar -tvf dist/edilkamin-*.tar.gz
```

Upload:

```sh
make release/upload
```

## Release notes

You may want to add some GitHub release notes, by attaching a release to
[the newly pushed tag](https://github.com/AndreMiras/edilkamin.py/tags).
