"""Access Bucket: code for performing operation on Object Store Buckets
"""
import mimetypes
import os

import boto3
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()

load_dotenv()


class AccessBucket:
    """Access Jasmin Class"""

    def __init__(
        self,
        bucket: str,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        endpoint_url: str = None,
    ) -> None:
        """
        AccessJasmin: class for convert netcdf to geotiff

        Args:
            bucket (str): bucket name
            aws_access_key_id (str, optional): bucket token
            aws_secret_access_key (str, optional): bucket secret
            endpoint_url (str, optional): bucket url
        Returns:
            None
        """

        if aws_access_key_id:
            self.__bucket_token = aws_access_key_id
        else:
            self.__bucket_token = os.environ.get("BUCKET_TOKEN")

        if aws_secret_access_key:
            self.__bucket_secret = aws_secret_access_key
        else:
            self.__bucket_secret = os.environ.get("BUCKET_SECRET")

        if endpoint_url:
            self.__bucket_api_url = endpoint_url
        else:
            self.__bucket_api_url = os.environ.get("BUCKET_API_URL")

        self.bucket = bucket
        self.client = boto3.client(
            aws_access_key_id=self.__bucket_token,
            aws_secret_access_key=self.__bucket_secret,
            endpoint_url=self.__bucket_api_url,
            service_name="s3",
            verify=False,
        )

    def upload(self, file_names=None, path="./", bucket_folder="output/", verbose=0):
        """
        upload: upload files into bucket

        Args:
            file_names (str[]): list of file names
            path (str, optional): location of the local files. If not provided,
        the data should be in the current folder
            bucket_folder (str): directory where the files will be saved on bucket
        """
        if bucket_folder:
            if bucket_folder[-1] != "/":
                bucket_folder += "/"
        if not file_names:
            for subdir, dirs, filenames in os.walk(path):
                print(dirs)
                for filename in filenames:
                    try:
                        full_path = os.path.join(subdir, filename)
                        mime_type = mimetypes.guess_type(full_path)[0]
                        with open(full_path, "rb") as local_file:
                            self.client.put_object(
                                ACL="public-read-write",
                                Body=local_file,
                                Bucket=self.bucket,
                                Key=f"{path}/{full_path[len(path)+1:]}",
                                ContentType=mime_type,
                            )
                        if verbose:
                            print(
                                f"Uploaded at s3://{self.bucket}/{path}/{full_path[len(path)+1:]}"
                            )
                    except TypeError as error:
                        print("Error: " + str(error))
        else:
            for filename in file_names:
                try:
                    print(filename, f"{path}{filename}")
                    mime_type = mimetypes.guess_type(f"{path}{filename}")[0]
                    with open(f"{path}{filename}", mode="rb") as local_file:
                        self.client.put_object(
                            # ACL="public-read-write",
                            Body=local_file,
                            Bucket=self.bucket,
                            Key=f"{bucket_folder}{filename}",
                            ContentType=mime_type,
                        )
                    if verbose:
                        print(
                            f"Uploaded file s3://{self.bucket}/{bucket_folder}{filename}"
                        )

                except TypeError as error:
                    print("Error: " + str(error))

    def rm(
        self,
        bucket_folder: str,
        filename: str = None,
        prefix: str = "",
        sufix: str = None,
        force: bool = False,
        verbose: int = 0,
    ):
        """
        rm: remove files from bucket

        Args:
            bucket_folder (str): irectory where the files will be removed
            filename (str, optional): name of the file that will be deleted. If it
        is not provided, all directory will be removed. Defaults to None.
            prefix (str, optional): prefix of the file that will be deleted. If it
        is not provided, all directory will be removed. Defaults to "".
            sufix (str, optional): sufix of the file that will be deleted. If it
        is not provided, all directory will be removed. Defaults to None.
            force (bool, optional): Remove file without asking. Defaults to False.
            verbose (int, optional): Print outputs. Defaults to 0.
        """

        if bucket_folder:
            if bucket_folder[-1] != "/":
                bucket_folder += "/"
        if not filename:
            objects = self.client.list_objects(
                Bucket=self.bucket, Prefix=f"{bucket_folder}{prefix}"
            )
            if sufix:
                objects["Contents"] = filter(
                    lambda obj: obj["Key"].endswith(sufix), objects["Contents"]
                )
        else:
            objects = {"Contents": [{"Key": f"{bucket_folder}{filename}"}]}
        try:
            for file_object in objects["Contents"]:
                if force:
                    self.client.delete_object(
                        Bucket=self.bucket, Key=file_object["Key"]
                    )
                    if verbose:
                        print(f"File s3://{self.bucket}/{file_object['Key']} removed!")
                else:
                    print(
                        f"You are going to remove s3://{self.bucket}/{file_object['Key']}"
                    )
                    if input("Are you sure? (y/n)") == "y":
                        self.client.delete_object(
                            Bucket=self.bucket, Key=file_object["Key"]
                        )
                        if verbose:
                            print(
                                f"File s3://{self.bucket}/{file_object['Key']} removed!"
                            )
        except TypeError as e:
            print("Error" + str(e))

        if not filename and not sufix and not prefix:
            if force:
                self.client.delete_object(Bucket=self.bucket, Key=bucket_folder)
                if verbose:
                    print(f"Directory s3://{self.bucket}/{bucket_folder} removed!")
            else:
                print(
                    f"You are going to remove directory s3://{self.bucket}/{bucket_folder}"
                )
                if input("Are you sure? (y/n)") == "y":
                    self.client.delete_object(Bucket=self.bucket, Key=bucket_folder)
                    if verbose:
                        print(f"Directory s3://{self.bucket}/{bucket_folder} removed!")

    def mkdir(self, bucket_folder, verbose=0):
        """
        mkdir: create folder on bucket

        Args:
            bucket_folder (str): directory name
            verbose (int, optional): Print outputs. Defaults to 0.
        """
        if bucket_folder:
            if bucket_folder[-1] != "/":
                bucket_folder += "/"
        try:
            self.client.put_object(
                ACL="public-read-write",
                Bucket=self.bucket,
                Key=f"{bucket_folder}/",
            )
            if verbose:
                print(f"Created folder s3://{self.bucket}/{bucket_folder}")
        except TypeError as e:
            print("Error" + str(e))

    def cp(self, bucket_folder, output_folder, filename=None, verbose=0):
        """
        cp: copy files and folder

        Args:
            bucket_folder (str): input directory name
            output_folder (str): output directory name
            filename (str): name of the file that will be copied. If it is
        not provided, it will copy all the folder
            verbose (int, optional): Print outputs. Defaults to 0.
        """
        if bucket_folder:
            if bucket_folder[-1] != "/":
                bucket_folder += "/"
        if output_folder[-1] != "/":
            output_folder += "/"

        if not filename:
            objects = self.client.list_objects(Bucket=self.bucket, Prefix=bucket_folder)
        else:
            objects = {"Contents": [{"Key": f"{bucket_folder}{filename}"}]}
        try:
            for file_object in objects["Contents"]:
                copy_source = {"Bucket": self.bucket, "Key": file_object["Key"]}
                self.client.copy_object(
                    Bucket=self.bucket,
                    CopySource=copy_source,
                    Key=f"{output_folder}{file_object['Key'].split('/')[-1]}",
                )
                if verbose:
                    print(
                        f"Copied s3://{self.bucket}/{bucket_folder}/{file_object['Key']} \
                            to s3://{self.bucket}/{output_folder}"
                    )
        except TypeError as e:
            print("Error" + str(e))

    def mv(
        self,
        bucket_folder,
        output_folder: str = None,
        file_format: str = None,
        prefix: str = "",
        sufix: str = None,
        replace: str = None,
        new_file_format: str = None,
        input_filename: str = None,
        output_filename: str = None,
        verbose: str = 0,
    ):
        """
        cp: copy files and folder

        Args:
            bucket_folder (str): directory where the files are located on the
        object store
            output_folder (str): directory where the files will be saved
            file_format (str): format of the input files
            prefix (str, optional): prefix of the file that will be moved/renamed.
        If it is not provided, all directory will be removed. Defaults to "".
            sufix (str, optional): sufix of the file that will be moved/renamed.
        If it is not provided, all directory will be removed. Defaults to None.
            force (bool, optional): Remove file without asking. Defaults to False.
            replace (str[]): replaces strings for the file name
            new_file_format (str): new format of the renamed files
            input_filename (str): old name of the renamed file
            output_filename (str): name of the renamed file
            verbose (int, optional): Print outputs. Defaults to 0.
        """

        if bucket_folder:
            if bucket_folder[-1] != "/":
                bucket_folder += "/"

        if not input_filename:
            objects = self.client.list_objects(
                Bucket=self.bucket, Prefix=f"{bucket_folder}{prefix}"
            )
            if sufix:
                objects["Contents"] = filter(
                    lambda obj: obj["Key"].endswith(sufix), objects["Contents"]
                )
        else:
            objects = {"Contents": [{"Key": f"{bucket_folder}{input_filename}"}]}

        if not output_folder:
            output_folder = bucket_folder
        if output_folder[-1] != "/":
            output_folder += "/"

        try:
            for file_object in objects["Contents"]:
                if file_format:
                    if file_object["Key"].split(".")[-1] != file_format:
                        continue
                copy_source = {"Bucket": self.bucket, "Key": file_object["Key"]}
                filename = file_object["Key"].split("/")[-1]
                if new_file_format:
                    filename = filename.split(".")[0] + "." + new_file_format
                if replace:
                    filename = filename.replace(replace[0], replace[1])
                if input_filename and output_filename:
                    filename = output_filename
                self.client.copy_object(
                    Bucket=self.bucket,
                    CopySource=copy_source,
                    Key=f"{output_folder}{filename}",
                )
                self.client.delete_object(Bucket=self.bucket, Key=file_object["Key"])
                if verbose:
                    print(
                        f"Moved/renamed s3://{self.bucket}/{file_object['Key']} \
                            to s3://{self.bucket}/{output_folder}{filename}"
                    )
        except TypeError as e:
            print("Error" + str(e))

    def ls(self, bucket_folder, prefix="", sufix=None):
        """
        ls: list files

        Args:
            bucket_folder (str): directory name
            prefix (str, optional): prefix of the files.
        If it is not provided, all directory will be removed. Defaults to "".
            sufix (str, optional): sufix of the files.
        If it is not provided, all directory will be removed. Defaults to None.
        """
        if bucket_folder:
            if bucket_folder[-1] != "/":
                bucket_folder += "/"
        objects = self.client.list_objects(
            Bucket=self.bucket, Prefix=f"{bucket_folder}{prefix}"
        )
        if sufix:
            objects["Contents"] = filter(
                lambda obj: obj["Key"].endswith(sufix), objects["Contents"]
            )
        try:
            for file_object in objects["Contents"]:
                print(file_object["Key"])
        except TypeError as e:
            print("Error" + str(e))
