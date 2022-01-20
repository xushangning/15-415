"""Design choices:
1. All tables are unmanaged, as we won't use migration to create or delete
tables. This is because migration can't use some features of the database,
like [multi-column primary keys](https://stackoverflow.com/questions/4871966/make-primary-key-with-2-fields-in-django)
or [enforcing foreign key constraints](https://code.djangoproject.com/ticket/21961).
If tables are created with migration, they won't have multi-column primary keys,
for example.
2. In models for many-to-many relationships like `Tag` and `Like`, we designate
a random column as the primary key so that ORM won't generate INSERT statements
that try to insert values into the ID column, which is automatically generated
by Django if there is no primary key. This work-around may have serious
implications e.g., when you want to delete a row in a many-to-many table using
the primary key. We will write raw SQL in such cases.
"""
from django.db import models


class TagName(models.Model):
    TAG_MAX_LENGTH = 50
    tagname = models.CharField(primary_key=True, max_length=TAG_MAX_LENGTH)

    class Meta:
        managed = False
        db_table = 'tagnames'


class Tag(models.Model):
    pid = models.ForeignKey('Paper', models.DO_NOTHING, db_column='pid', primary_key=True)
    tagname = models.ForeignKey(TagName, models.DO_NOTHING, db_column='tagname')

    class Meta:
        managed = False
        db_table = 'tags'


class User(models.Model):
    USERNAME_MAX_LENGTH = 50
    PASSWORD_MAX_LENGTH = 32

    username = models.CharField(primary_key=True, max_length=USERNAME_MAX_LENGTH)
    password = models.CharField(max_length=PASSWORD_MAX_LENGTH)

    class Meta:
        managed = False
        db_table = 'users'


class Paper(models.Model):
    TITLE_MAX_LENGTH = 50
    DESCRIPTION_MAX_LENGTH = 500

    pid = models.AutoField(primary_key=True)
    username = models.ForeignKey(User, models.DO_NOTHING, db_column='username')
    title = models.CharField(max_length=TITLE_MAX_LENGTH, blank=True, null=True)
    begin_time = models.DateTimeField()
    description = models.CharField(max_length=DESCRIPTION_MAX_LENGTH, blank=True, null=True)
    data = models.TextField(blank=True, null=True)
    tag_names = models.ManyToManyField(TagName, through=Tag, through_fields=('pid', 'tagname'))
    liked_users = models.ManyToManyField(
        User,
        through='Like', through_fields=('pid', 'username'),
        related_name='liked_papers',
    )

    class Meta:
        managed = False
        db_table = 'papers'


class Like(models.Model):
    pid = models.ForeignKey(Paper, models.DO_NOTHING, db_column='pid', primary_key=True)
    username = models.ForeignKey(User, models.DO_NOTHING, db_column='username')
    like_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'likes'
