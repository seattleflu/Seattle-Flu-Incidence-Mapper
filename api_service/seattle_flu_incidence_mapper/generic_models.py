# API Methods for the /pathogen_models calls
import hashlib
from typing import Tuple

from seattle_flu_incidence_mapper.model_store import save_model_file, get_model_file
from seattle_flu_incidence_mapper.models.generic_model import GenericModel, GenericModelSchema
from seattle_flu_incidence_mapper.config import db
from flask import abort, request, make_response, send_file
from seattle_flu_incidence_mapper.utils import get_model_id

def read_all():
    """
    This function responds to a request for /api/pathogen_models
    with the complete lists of models
    :return:        json string of list of models
    """
    # Create the list of pathogen_models from our data

    # Create the list of pathogen_models from our data
    pathogen_models = GenericModel.query.order_by(GenericModel.created.desc()).all()

    # Serialize the data for the response
    pathogen_model_schema = GenericModelSchema(many=True)
    data = pathogen_model_schema.dump(pathogen_models).data
    return data


def read(model_id):
    """
    This function responds to a request for /api/pathogen_models/{pathogen_model_id}
    with one matching pathogen_model from pathogen_models

    Args:
        model_id: Id of pathogen_model to find

    Returns: pathogen_model matching id

    """

    # Get the pathogen_model requested
    pathogen_model = GenericModel.query.filter(GenericModel.id == model_id).one_or_none()

    # Did we find a pathogen_model?
    if pathogen_model is not None:

        # Serialize the data for the response
        pathogen_model_schema = GenericModelSchema()
        data = pathogen_model_schema.dump(pathogen_model).data
        return data

    # Otherwise, nope, didn't find that pathogen_model
    else:
        abort(
            404,
            "Pathogen Model not found for Id: {id}".format(id=model_id),
        )


def create():
    """
    This function creates a new pathogen_model in the pathogen_models structure
    based on the passed in pathogen_model data

    Returns:
        201 on success, 406 on pathogen_model exists
    """
    schema = None
    new_model = None
    # if the item comes in as a single, let's [
    if type(request.form['name']) is str:
        new_model, schema = insert_one_model(form=request.form, files=request.files)
    else:
        for i in range(len(request.form['name'])):
            new_model, schema = insert_one_model(form={k: request.form[k][i] for k in request.keys()},
                                                          files={k: request.form[k][i] for k in request.files.keys()})
    db.session.commit()
    if schema and new_model:

        # Serialize and return the newly created pathogen_model in the response
        data = schema.dump(new_model).data

        return data, 201
    return "Unknown error", 400


def insert_one_model(form, files) -> Tuple[GenericModel, GenericModelSchema]:
    """
    Insert a model into the database

    Args:
        form: Dict representing the post form
        files: Dict with files that were uploaded

    Returns:
        A GenericModel
    """
    rds_key = None
    model_key = None
    if 'rds' in request.files:
        rds_key = hashlib.md5(files['rds'].read()).hexdigest()
    if 'model' in request.files:
        model_key = hashlib.md5(files['model'].read()).hexdigest()
    model_id = get_model_id(form['query_str'])

    # build our pathogen model object first
    model = dict(id=model_id,
                 name=form['name'],
                 query_str=form['query_str'],
                 rds_key=rds_key,
                 model_type=form['model_type'],
                 model_key=model_key)
    schema = GenericModelSchema()
    new_model = schema.load(model, session=db.session).data
    # Add the pathogen_model to the database
    db.session.add(new_model)

    # save the files to our config directory
    save_model_file(files['model'], f'{new_model.id}')
    return new_model, schema


def update(pathogen_model_id, pathogen_model):
    """
    This function updates an existing pathogen_model in the pathogen_models structure

    Args:
        pathogen_model_id: Id of the pathogen_model to update in the pathogen_models structure
        pathogen_model: pathogen_model to update

    Returns:
        updated pathogen_model structure
    """
    # Get the pathogen_model requested from the db into session
    update_pathogen_model = GenericModel.query.filter(
        GenericModel.id == pathogen_model_id
    ).one_or_none()

    # Did we find a pathogen_model?
    if update_pathogen_model is not None:

        # turn the passed in pathogen_model into a db object
        schema = GenericModelSchema()
        updated = schema.load(pathogen_model, session=db.session).data

        # Set the id to the pathogen_model we want to update
        updated.id = update_pathogen_model.id

        # merge the new object into the old and commit it to the db
        db.session.merge(updated)
        db.session.commit()

        # return updated pathogen_model in the response
        data = schema.dump(update_pathogen_model).data

        return data, 200

    # Otherwise, nope, didn't find that pathogen_model
    else:
        abort(
            404,
            "Pathogen Model not found for Id: {pathogen_model_id}".format(pathogen_model_id=pathogen_model_id),
        )


def delete(pathogen_model_id):
    """
    This function deletes a pathogen_model from the pathogen_models structure

    Args:
        pathogen_model_id: Id of the pathogen_model to delete

    Returns:
        200 on successful delete, 404 if not found
    """
    # Get the pathogen_model requested
    pathogen_model = GenericModel.query.filter(GenericModel.id == pathogen_model_id).one_or_none()

    # Did we find a pathogen_model?
    if pathogen_model is not None:
        db.session.delete(pathogen_model)
        db.session.commit()
        return make_response(
            "Pathogen Model {pathogen_model_id} deleted".format(pathogen_model_id=pathogen_model_id), 200
        )

    # Otherwise, nope, didn't find that pathogen_model
    else:
        abort(
            404,
            "Pathogen Model not found for Id: {pathogen_model_id}".format(pathogen_model_id=pathogen_model_id),
        )
