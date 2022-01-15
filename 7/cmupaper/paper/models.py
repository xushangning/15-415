"""Design choices:
1. All tables are unmanaged, as we won't use migration to create or delete
tables. This is because migration can't use some features of the database,
like [multi-column primary keys](https://stackoverflow.com/questions/4871966/make-primary-key-with-2-fields-in-django)
or [enforcing foreign key constraints](https://code.djangoproject.com/ticket/21961).
If tables are created with migration, they won't have multi-column primary keys,
for example.
"""
from django.db import models


class Tagnames(models.Model):
    tagname = models.CharField(primary_key=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'tagnames'


class Tags(models.Model):
    pid = models.ForeignKey('Papers', models.DO_NOTHING, db_column='pid')
    tagname = models.ForeignKey(Tagnames, models.DO_NOTHING, db_column='tagname')

    class Meta:
        managed = False
        db_table = 'tags'


class Users(models.Model):
    USERNAME_MAX_LENGTH = 50
    PASSWORD_MAX_LENGTH = 32

    username = models.CharField(primary_key=True, max_length=USERNAME_MAX_LENGTH)
    password = models.CharField(max_length=PASSWORD_MAX_LENGTH)

    class Meta:
        managed = False
        db_table = 'users'


class Papers(models.Model):
    pid = models.AutoField(primary_key=True)
    username = models.ForeignKey(Users, models.DO_NOTHING, db_column='username')
    title = models.CharField(max_length=50, blank=True, null=True)
    begin_time = models.DateTimeField()
    description = models.CharField(max_length=500, blank=True, null=True)
    data = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'papers'


class Likes(models.Model):
    pid = models.ForeignKey(Papers, models.DO_NOTHING, db_column='pid')
    username = models.ForeignKey(Users, models.DO_NOTHING, db_column='username')
    like_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'likes'
