SCRIPT_DIR=`dirname "$0"`
DATASET_INFO_FILES_DIR=/hive/users/shirey/manual-data-ingest/t
COPY_FROM_DIR=/hive/hubmap/data
COPY_TO_DIR=/hive/hubmap-dev/data-next
ASSETS_DIR=/hive/hubmap-dev/assets-next

cat $DATASET_INFO_FILES_DIR/public-derived-dataset-dirs-new.txt | parallel -j 20 rsync -avP --stats $COPY_FROM_DIR/public/{} $COPY_TO_DIR/public/
cat $DATASET_INFO_FILES_DIR/protected-derived-dataset-dirs.txt | sed 's/\\//g' | parallel -j 20 rsync -avP --stats $COPY_FROM_DIR/protected/{} $COPY_TO_DIR/protected/{//}/
cat $DATASET_INFO_FILES_DIR/consortium-derived-dataset-dirs.txt | sed 's/\\//g' | parallel -j 20 rsync -avP --stats $COPY_FROM_DIR/consortium/{} $COPY_TO_DIR/consortium/{//}/

find $ASSETS_DIR/ -maxdepth 1 -type l -exec unlink {} \;
cat $DATASET_INFO_FILES_DIR/public-derived-dataset-dirs-new.txt | parallel -j 20 ln -s $COPY_TO_DIR/public/{} $ASSETS_DIR/{}
cat $DATASET_INFO_FILES_DIR/consortium-derived-dataset-dirs.txt | sed 's/\\//g' | parallel -j 20 ln -s $COPY_TO_DIR/consortium/{} $ASSETS_DIR/{/}


cat $DATASET_INFO_FILES_DIR/protected-dataset-dirs.txt | sed 's/\\//g' | parallel -j 20 $SCRIPT_DIR/create-readme.sh /hive/hubmap-dev/data-next/protected/{}
cat $DATASET_INFO_FILES_DIR/consortium-dataset-dirs.txt | sed 's/\\//g' | parallel -j 20 $SCRIPT_DIR/create-readme.sh /hive/hubmap-dev/data-next/consortium/{}
cat $DATASET_INFO_FILES_DIR/public-dataset-dirs.txt | parallel -j 20 ./create-readme.sh /hive/hubmap-dev/data-next/public/{/}


chown -Rh hive:hive $ASSETS_DIR
cat $DATASET_INFO_FILES_DIR/protected-dataset-dirs.txt | sed 's/\\//g' | parallel -j 20 setfacl -R --set=u::rwx,g::r-x,o::-,m::rwx,u:hive:rwx,u:shirey:rwx,g:hubseq:r-x,d:user::rwx,d:user:hive:rwx,d:user:shirey:rwx,d:group:hubseq:r-x,d:group::r-x,d:mask::rwx,d:other:--- $COPY_TO_DIR/protected/{}
cat $DATASET_INFO_FILES_DIR/consortium-dataset-dirs.txt  | sed 's/\\//g' | parallel -j 20 setfacl -R --set=u::rwx,g::r-x,o::r-x,m::rwx,u:hive:rwx,u:shirey:rwx,d:user::rwx,d:user:hive:rwx,d:user:shirey:rwx,d:group::r-x,d:mask::rwx,d:other:r-x $COPY_TO_DIR/consortium/{}
cat $DATASET_INFO_FILES_DIR/public-dataset-dirs-new.txt | parallel -j 20 setfacl -R --set=u::rwx,g::r-x,o::-,m::rwx,u:hive:rwx,u:shirey:rwx,g:hubmap:r-x,d:user::rwx,d:user:hive:rwx,d:user:shirey:rwx,d:group:hubmap:r-x,d:group::r-x,d:mask::rwx,d:other:--- $COPY_TO_DIR/public/{}

