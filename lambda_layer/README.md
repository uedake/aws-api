
## AWS Lambdaレイヤー作成用イメージ

AWS Lambdaレイヤーを作成する為のイメージです
イメージはOSとしてamazonlinux 2023を用いています

OSとlambdaランタイムの関係は下記を参照してください
https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html

本イメージを用いると例えば、python 3.12用のLambdaレイヤーを作成可能です


## Lambdaレイヤー作成方法

1. イメージをビルド

```
cd lambda_layer/docker
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

## Lambdaレイヤーアップロード方法

### (推奨)uploadスクリプトを使用する場合

uploadスクリプトは同名レイヤーの最新バージョンとzipファイルのhashが一致する場合、アップロードをキャンセルします
（ただし、Lambdaレイヤーのzipはまったく同じパラメータで作成しても作成するたびにhashが異なります）

```
cd lambda_layer
python .\upload.py .\sample\3.12.3_numpy_numpy-quaternion\layer.zip numpy_numpy-quaternion python3.12
```

### aws cliを使用する場合

```
aws lambda publish-layer-version --zip-file fileb://.\sample\3.12.3_numpy_numpy-quaternion\layer.zip --layer-name numpy_numpy-quaternion --compatible-runtimes '[\"python3.12\"]' --compatible-architectures '[\"x86_64\"]'
```
