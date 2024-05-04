
## AWS Lambdaレイヤー作成用イメージ

AWS Lambdaレイヤーを作成する為のイメージです
イメージはOSとしてamazonlinux 2023を用いています

OSとlambdaランタイムの関係は下記を参照してください
https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html

本イメージを用いると例えば、python 3.12用のLambdaレイヤーを作成可能です

## 使い方

1. イメージをビルド

```
cd path/to/directory
docker build -t al2023py .
```

2. Lambdaレイヤーを作成

Lambdaレイヤーはlayer.zipという名称で指定のフォルダに出力されます

- 出力先フォルダは、下記の通りローカルフォルダをコンテナ内の/distにマウントして呼び出すことで指定します。
- pythonのversionを第１引数で指定します
- インストールしたいpython packageを第２引数以降で指定します
  - 第２引数以降はpip install で指定できる引数が全て使用できます。-r requirements.txt等も使用できます

例えば、カレントディレクトリに出力、python 3.12.3を使用、pandasをインストールする場合は下記の通り実行します

```
docker run --rm -v $(pwd):/dist al2023py 3.12.3 pandas
```