# lambda_layer

pythonランタイムのAWS Lambdaレイヤーを作成する為のdockerイメージです

- 本イメージを用いるとpython用のLambdaレイヤーを作成可能です
- その他、amazonlinuxのversionとpythonのversionを指定することで任意のpythonランタイムのLambdaレイヤーも作成可能です
- OSとpythonランタイムの関係は下記を参照してください
  - https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html


## Lambdaレイヤー作成方法

下記２つの方法のいずれかを実行ください

- おまかせ作成（推奨）
- マニュアル作成

### おまかせ作成

lambdaレイヤーの作成からアップロードまで一貫して行います
最低限下記を指定してcraete_upload.pyを実行してください
- <layer_name>
  - 作りたいレイヤー名を指定します（AWS lambda上での識別名）
- <pip_install_args>
  - レイヤーに入れたいpythonパッケージを指定

例１：下記ではpython3.13向けにlambdaレイヤーを作成します
```
cd path/to/lambda_layer
python craete_upload.py <layer_name> <pip_install_args>
```

例２：下記はpython3.12.3向けにlambdaレイヤーを作成します
```
cd path/to/lambda_layer
python craete_upload.py -a 2 -p 3.12.3 <layer_name> <pip_install_args>
```

<pip_install_args>で-rのオプションを指定する場合は"-r mount/sample/requirements.txt"のように""で囲い、mountフォルダからのパスをしてしてください。
注：dokcerコンテナから読み出せるようにrequirements.txtはmountフォルダ以下に置く必要があります

例：
```
cd path/to/lambda_layer
python craete_upload.py py3-12-sample "-r sample/requirements.txt"
```


### マニュアル作成

下記を順に実行してください

1. dockerイメージをbuild

例１：下記ではpython3.13向けにlambdaレイヤーを作成します
```
cd lambda_layer/docker/amazonlinux2023
docker build -t lambda-layer-build --build-arg PYTHON_VER=3.13 .
```

例２：下記ではpython3.12.3向けにlambdaレイヤーを作成します
```
cd lambda_layer/docker/amazonlinux2
docker build -t lambda-layer-build --build-arg PYTHON_VER=3.12.3 .
```

2. dockerイメージをrunしてLambdaレイヤー（zip）を作成

```
cd lambda_layer
docker run --rm -v "mount:/mount" lambda-layer-build layer.zip <pip_install_args>
```

- 出力先フォルダは、上記の通りローカルフォルダmountをコンテナ内の/mountにマウントして呼び出すことで指定します。
- 出力ファイル名を第１引数で指定します
- インストールしたいpython packageを第２引数以降で指定します
  - 第２引数以降はpip install で指定できる引数が全て使用できます。-r requirements.txt等も使用できます
- lambdaレイヤーのzipファイルがmountフォルダ内に生成されます

例：numpyをインストールする場合
```
cd lambda_layer
docker run --rm -v "mount:/dist" lambda-layer-build layer.zip numpy
```

3. アップロード

例１：upload.pyスクリプトを使用する場合
```
cd lambda_layer
python upload.py mount/layer.zip py3-12-numpy python3.12
```

例２：AWS cliを使用する場合
```
aws lambda publish-layer-version --zip-file fileb://./mount//layer.zip --layer-name py3-12-numpy --compatible-runtimes '[\"python3.12\"]' --compatible-architectures '[\"x86_64\"]'
```
